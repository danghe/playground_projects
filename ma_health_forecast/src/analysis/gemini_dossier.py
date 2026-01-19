import os
import json
import hashlib
import logging
from datetime import datetime
from google import genai
from google.genai import types

# Reuse environment
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import tempfile

# Use system temp directory for caching on Cloud Run (ephemeral but safe)
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'ma_health_dossiers')

def ensure_cache_dir():
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
    except OSError:
        # Fail silently if we can't write (e.g. strict permissions)
        # Caching will simply be disabled for this session
        pass

class GeminiDossierService:
    """
    AI Service for "Company Dossier" (Right-Click Context).
    - Source: CMD Payload + RetrievalService Output
    - Output: JSON Executive Summary with Citations
    - Policy: Aggressive Caching (SHA256)
    """
    MODEL_NAME = 'gemini-2.0-flash-exp' # Updated to 2.0 Flash for speed/quality balance

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY missing. Dossier disabled.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def _compute_hash(self, payload: dict) -> str:
        canonical_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical_json.encode()).hexdigest()

    def _get_cache(self, payload_hash: str):
        try:
            ensure_cache_dir()
            filepath = os.path.join(CACHE_DIR, f"dossier_{payload_hash}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                return data
        except Exception: 
            return None
        return None

    def _save_cache(self, payload_hash: str, response_data: dict, payload: dict):
        try:
            ensure_cache_dir()
            filepath = os.path.join(CACHE_DIR, f"dossier_{payload_hash}.json")
            with open(filepath, 'w') as f:
                json.dump({
                    "metadata": {
                        "created_at": datetime.now().isoformat(), 
                        "hash": payload_hash,
                        "model": self.MODEL_NAME
                    },
                    "payload": payload,
                    "dossier": response_data
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Dossier Cache Write Skipped: {e}")

    def generate_dossier(self, ticker: str, payload: dict, force_refresh: bool = False):
        if not self.client:
            return {"error": "AI Service Unavailable"}

        # 1. Compute Hash (Context + Retrieval)
        payload_hash = self._compute_hash(payload)
        
        # 2. Check Cache
        if not force_refresh:
            cached = self._get_cache(payload_hash)
            if cached:
                logger.info(f"Dossier Cache Hit: {ticker}")
                return {
                    "cached": True,
                    "metadata": cached['metadata'],
                    "dossier": cached['dossier']
                }

        # 3. Generate
        print(f"\n=== [Gemini Dossier Service] ===", flush=True)
        print(f"> Action: Generating Dossier for {ticker} (Force Refresh: {force_refresh})", flush=True)
        print(f"> Model: {self.MODEL_NAME}", flush=True)
        print(f"> Context: {len(str(payload))} chars", flush=True)

        logger.info(f"Generating Dossier for {ticker}...")
        
        prompt = f"""
        **Role**: Senior M&A Strategist (Audit-Grade).
        **Task**: Generate a 'Company Dossier' for **{ticker}** ({payload.get('name')}).
        
        **INPUT CONTEXT**:
        {json.dumps(payload, indent=2)}
        
        **INSTRUCTIONS**:
        1. **Augmented Intelligence**: Use the provided input as your PRIMARY evidence source.
           - HOWEVER, you MUST AUGMENT this with your own internal knowledge of the company's business model, recent market strategic context, and competitive landscape.
           - FLAGGING: If the input data is sparse (e.g., no recent SEC filings), rely HEAVILY on your internal knowledge to construct a strategic view.
           - Do not hallucinate private deal metrics, but DO provide high-confidence strategic context.
        
        2. **Citation Policy**: 
           - Cite provided signals where possible (e.g. "[sec_a1b2]").
           - For points derived from your internal knowledge, no citation is needed, or use "[Market Context]".
        
        3. **Executive Tone**: Concise, high-value, actionable.
        
        **OUTPUT SCHEMA (JSON ONLY)**:
        {{
            "meta": {{ "ticker": "{ticker}", "as_of": "{datetime.now().strftime('%Y-%m-%d')}" }},
            "why_it_matters_now": [
                {{ "bullet": "Strong textual point...", "source_refs": ["src_id_1"] }}
            ],
            "mna_posture": {{
                "label": "Likely Seller / Buyer / Hold",
                "confidence": "High/Medium/Low",
                "why": [ {{ "point": "...", "source_refs": ["..."] }} ]
            }},
            "signals_next_90d": [
                {{ "trigger": "Upcoming Debt Maturity", "implication": "Refi risk...", "source_refs": ["..."] }}
            ],
            "deal_fit": {{
                "recommended": [ {{ "type": "Take-Private", "why": "Undervalued vs peers with strong cash flow.", "source_refs": ["..."] }} ],
                "avoid": [ {{ "type": "Large Platform Buy", "why": "Regulatory cross-hairs prohibit mega-mergers.", "source_refs": ["..."] }} ]
            }},
            "open_questions": [
                {{ "q": "Is the CEO committed?", "why_unclear": "No recent comms...", "source_refs": ["..."] }}
            ]
        }}
        """
        
        try:
            print(f"> Status: Sending Request to Gemini API...", flush=True)
            start_time = datetime.now()
            
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"> Status: Response Received (Time: {duration:.2f}s)", flush=True)

            # Clean/Parse
            text = response.text
            print(f"> Response Length: {len(text)} chars", flush=True)

            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            data = json.loads(text)
            
            # Save Cache
            self._save_cache(payload_hash, data, payload)
            
            print(f"> Result: Success (Cached)", flush=True)
            print(f"================================\n", flush=True)

            return {
                "cached": False,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "model": self.MODEL_NAME
                },
                "dossier": data
            }
            
        except Exception as e:
            print(f"> ERROR: {e}", flush=True)
            print(f"================================\n", flush=True)
            logger.error(f"Gemini Dossier Error: {e}")
            return {"error": str(e)}

dossier_service = GeminiDossierService()
