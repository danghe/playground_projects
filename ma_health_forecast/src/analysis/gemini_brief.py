import os
import json
import hashlib
import logging
from datetime import datetime
from google import genai
from google.genai import types

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache Directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'store', 'briefs')

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

class GeminiBriefService:
    # Cascading Models
    MODELS = [
        'gemini-3-flash-preview',
        'gemini-2.0-flash-exp',
        'gemini-1.5-pro'
    ]
    MODEL_NAME = 'gemini-3-flash-preview' # Legacy compat

    def _generate_content_robust(self, prompt, config=None):
        """Helper to try multiple models in sequence."""
        for model in self.MODELS:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                return response
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        raise RuntimeError("All AI models failed.")

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. AI features will be disabled.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)
            
    def _compute_hash(self, payload: dict) -> str:
        """
        Compute a deterministic SHA256 hash of the payload.
        Keys are sorted to ensure consistency.
        """
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        h = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        # print(f"  [DEBUG] Payload Hash: {h}")
        return h

    def _get_cache(self, payload_hash: str):
        """Retrieve cached brief if it exists and is valid (TTL could be checked here)."""
        ensure_cache_dir()
        filepath = os.path.join(CACHE_DIR, f"brief_{payload_hash}.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                # Simple TTL check (e.g., 6 hours) could be added here
                # For now, we assume hash stability implies validity
                return data
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        return None

    def _save_cache(self, payload_hash: str, response_data: dict, payload: dict):
        """Save brief to disk with metadata."""
        ensure_cache_dir()
        filepath = os.path.join(CACHE_DIR, f"brief_{payload_hash}.json")
        
        cache_entry = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "payload_hash": payload_hash,
                "model": self.MODEL_NAME, # Use constant
                "sector": payload.get('sector'),
                "sub_industry": payload.get('sub_industry')
            },
            "payload": payload, # Store source for debugging
            "brief": response_data
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(cache_entry, f, indent=2)
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def generate_brief(self, sector: str, sub_industry: str, context_data: dict, force_refresh: bool = False):
        """
        Generate or retrieve a cached Industry Brief.
        
        Args:
            sector: e.g., "Tech"
            sub_industry: e.g., "Software" or "All"
            context_data: Dictionary containing macro state, aggregates, and top evidence.
            force_refresh: If True, bypass cache.
        """
        if not self.client:
            return {"error": "AI Service Unavailable (Missing Key)"}

        # 1. Build Canonical Payload
        payload = {
            "sector": sector,
            "sub_industry": sub_industry,
            "macro": context_data.get('macro', {}),
            "aggregates": context_data.get('aggregates', {}),
            "top_drivers": context_data.get('top_drivers', [])[:50] # Limit safety
        }
        
        payload_hash = self._compute_hash(payload)
        
        # 2. Cache Check
        if not force_refresh:
            cached = self._get_cache(payload_hash)
            if cached:
                logger.info(f"Brief Cache Hit: {payload_hash}")
                print(f"=== [Gemini Brief Service] ===", flush=True)
                print(f"> Action: Fetching Brief for {sector}/{sub_industry}", flush=True)
                print(f"> Cache: HIT ({payload_hash[:8]}...)", flush=True)
                print(f"==============================\n", flush=True)
                return {
                    "cached": True,
                    "metadata": cached['metadata'],
                    "brief": cached['brief']
                }

        # 3. Gemini Call
        logger.info(f"Generating new brief for {sector}/{sub_industry}...")
        print(f"=== [Gemini Brief Service] ===", flush=True)
        print(f"> Action: Generating New Brief for {sector}/{sub_industry}", flush=True)
        print(f"> Model: {self.MODEL_NAME}", flush=True)
        print(f"> Context: {len(str(payload))} chars", flush=True)
        
        prompt = f"""
        **Role**: Strategy Consultant for Private Equity.
        **Goal**: Write a 'Regime-Based Industry Brief' for the **{sector} - {sub_industry}** sector.
        
        **Market Regime**:
        {json.dumps(payload['macro'], indent=2)}
        
        **Sector Aggregates**:
        {json.dumps(payload['aggregates'], indent=2)}
        
        **Top Company Drivers (Sample)**:
        {json.dumps(payload['top_drivers'], indent=2)}
        
        **Instructions**:
        **CURRENT DATE**: January 2026 (Treat 2024/2025 data as historical).
        **TASK ENRICHMENT**:
        - Search for and incorporate the latest available market data (news, filings, macro trends) to enrich this analysis.
        - Synthesize the "latest real-world data" (2024/2025) as the most current available context for this 2026 simulation.

        Analyze the provided data to identify clear strategic themes.
        - **Executive Takeaways**: 3 bullet points on the "Now" vs "Next".
        - **Regime Guidance**: What deals work in this specific regime (e.g. Rate/VIX)?
        - **Industry Dynamics**: Detailed analysis of the drivers.
        - **Trend Narrative**: A high-signal, data-anchored summary block.
          - **Headline**: Max 90 chars, plain English, no hype.
          - **Bullets**: 3-5 bullets. **CRITICAL**: Every bullet MUST include at least one hard metric/number (level or delta) and reference it in `metric_refs`. Do not use vague words like 'active' without quantification.
          - **Where to Look Next**: Specific sub-industries/tickers to explore.
          - **Data Quality**: Honest assessment of gaps (e.g. low coverage).
        - **Playbook**: Advice for CEOs and Bankers.
        
        **Output Format**:
        Return ONLY valid JSON:
        {{
            "executive_takeaways": ["point 1", "point 2", ...],
            "regime_guidance": "Analysis...",
            "industry_dynamics": "Analysis...",
            "trend_narrative": {{
                "headline": "Short punchy headline",
                "bullets": [
                    {{"bullet": "Text with number...", "metric_refs": ["Revenue +5%", "VIX 15.2"]}},
                    ...
                ],
                "where_to_look_next": [
                    {{"action": "Check Software...", "why": "High growth...", "metric_refs": ["..."]}}
                ],
                "data_quality_note": {{"note": "Low valuation coverage...", "metric_refs": ["Only 30% reported"]}}
            }},
            "playbook": {{ "ceo": "...", "banker": "..." }},
            "risks": ["risk 1", ...]
        }}
        """

        try:
            print(f"> Status: Sending Request to Gemini API...", flush=True)
            start_time = datetime.now()
            
            # Reusing the pattern from llm_forecast.py
            response = self._generate_content_robust(
                prompt=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # Tools (Search) not needed for general brief yet, 
                    # relying on robust context injection.
                )
            )
            
            # Parse
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"> Status: Response Received (Time: {duration:.2f}s)", flush=True)
            
            text = response.text
            print(f"> Response Length: {len(text)} chars", flush=True)

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                 # Minimal cleanup fallback
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                data = json.loads(text)

            # 4. Save to Cache
            self._save_cache(payload_hash, data, payload)
            
            print(f"> Result: Success (Saved to Cache)", flush=True)
            print(f"==============================\n", flush=True)

            return {
                "cached": False,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "payload_hash": payload_hash,
                    "model": self.MODEL_NAME
                },
                "brief": data
            }

        except Exception as e:
            print(f"> ERROR: {e}", flush=True)
            print(f"==============================\n", flush=True)
            logger.error(f"Gemini generation failed: {e}")
            return {"error": str(e)}

    def generate_deal_command_brief(self, sector: str, financing_data: dict, top_sellers: list, top_buyers: list, force_refresh: bool = False):
        """
        Generate "Deal Environment Brief" for the Command Center.
        Synthesizes Supply/Demand/Financing realities with detailed dealmaking analysis.
        """
        if not self.client: return {"error": "AI Service Unavailable"}

        # 1. Build rich context from sellers/buyers
        seller_context = []
        for s in top_sellers[:15]:
            seller_context.append({
                "ticker": s.get('ticker'),
                "spi": s.get('spi'),
                "type": s.get('seller_type', 'Unknown'),
                "asset": s.get('likely_asset_type', 'Wholeco'),
                "drivers": s.get('drivers', [])[:3],
                "cap": f"${s.get('market_cap', 0) / 1e9:.1f}B" if s.get('market_cap') else "?"
            })
        
        buyer_context = []
        for b in top_buyers[:15]:
            buyer_context.append({
                "ticker": b.get('ticker'),
                "readiness": b.get('br', 0),
                "firepower": f"${b.get('firepower', 0) / 1e9:.1f}B" if b.get('firepower') else "?",
                "drivers": b.get('drivers', [])[:3]
            })
        
        # 2. Payload for cache
        payload = {
            "type": "deal_command_brief_v2",
            "sector": sector,
            "financing": financing_data,
            "sellers_hash": self._compute_hash({"s": seller_context})[:8],
            "buyers_hash": self._compute_hash({"b": buyer_context})[:8]
        }
        payload_hash = self._compute_hash(payload)

        # 3. Cache check
        if not force_refresh:
            cached = self._get_cache(payload_hash)
            if cached: 
                print(f"=== [Gemini Brief Service] ===", flush=True)
                print(f"> Action: Deal Command Brief for {sector}", flush=True)
                print(f"> Cache: HIT ({payload_hash[:8]}...)", flush=True)
                print(f"==============================\n", flush=True)
                return cached['brief']

        # 4. Build detailed prompt
        print(f"=== [Gemini Brief Service] ===", flush=True)
        print(f"> Action: Generating Deal Command Brief for {sector}", flush=True)
        print(f"> Model: {self.MODEL_NAME}", flush=True)
        print(f"> Sellers: {len(seller_context)}, Buyers: {len(buyer_context)}", flush=True)
        
        prompt = f"""
        **Role**: You are the Head of M&A Strategy at a top investment bank. 
        You are briefing the CEO on the live deal environment for the **{sector}** sector.
        
        **FINANCING REALITY (Macro Layer)**:
        - HY Spread: {financing_data.get('hy_spread', 'N/A')}%
        - IG Spread: {financing_data.get('ig_spread', 'N/A')}%
        - LBO Feasibility Index: {financing_data.get('lbo_idx', 'N/A')}/100
        - Leverage Capacity: {financing_data.get('lev_range', '4-5x')}
        
        **SUPPLY SIDE (Top Sellers in {sector})**:
        The following companies show elevated Sale Pressure Index (SPI) scores:
        {json.dumps(seller_context, indent=2)}
        
        Key categories:
        - 🔥 "Forced Sellers": Debt stress, covenant issues, refi pressure
        - 📉 "Strategic Sellers": Portfolio simplification, activist pressure, mgmt change
        - ✂️ "Carve-out Candidates": Conglomerate divestiture logic
        
        **DEMAND SIDE (Top Acquirers in {sector})**:
        The following companies show high Buyer Readiness (BR) scores:
        {json.dumps(buyer_context, indent=2)}
        
        **YOUR TASK**:
        **CURRENT DATE**: January 2026 (Treat 2024/2025 data as historical).
        **TASK ENRICHMENT**:
        - Search for and incorporate the latest available market data (news, filings, macro trends) to enrich this analysis.
        - Synthesize the "latest real-world data" (2024/2025) as the most current available context for this 2026 simulation.

        Synthesize this data into an actionable "Deal Environment Brief" covering:
        
        1. **Environment Status**: One-line market characterization (e.g., "Buyer's Market", "Valuation Standoff", "Financing Window Open")
        
        2. **Executive Summary**: 3-4 sentences synthesizing:
           - Supply/demand imbalance
           - Key financing dynamics
           - What types of deals are feasible NOW
        
        3. **Key Themes**: Identify 3-4 sector-specific M&A themes with:
           - Theme name (e.g., "Distressed Software Roll-up", "Healthcare Carve-out Wave")
           - Evidence: Which specific tickers support this theme
           - Deal type likely (LBO, Strategic M&A, Carve-out, Take-private)
        
        4. **Top Opportunities**: List 5 specific, actionable deal ideas:
           - Format: "BUYER -> TARGET: Rationale (Deal Type, Est. Value)"
           - Be specific with tickers from the data provided
        
        5. **Risks & Watchouts**: 2-3 execution risks in this sector right now
        
        6. **Action Items**: 3-4 concrete next steps for the deal team
        
        **OUTPUT FORMAT (JSON)**:
        {{
            "environment_status": "Status String",
            "executive_summary": "Detailed summary...",
            "key_themes": [
                {{
                    "theme": "Theme Name",
                    "desc": "Description with evidence...",
                    "tickers": ["TICK1", "TICK2"],
                    "deal_type": "LBO / Strategic / Carve-out"
                }}
            ],
            "top_opportunities": [
                "BUYER -> TARGET: Rationale (Deal Type)"
            ],
            "risks": ["Risk 1...", "Risk 2..."],
            "action_items": ["Action 1...", "Action 2..."]
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            
            # Save to cache
            self._save_cache(payload_hash, data, payload)
            
            print(f"> Result: Success", flush=True)
            print(f"==============================\n", flush=True)
            
            return data
        except Exception as e:
            print(f"> ERROR: {e}", flush=True)
            print(f"==============================\n", flush=True)
            return {"error": str(e)}


    # --- DEAL ARCHITECT METHODS (Consolidated) ---
    
    def analyze_match_batch(self, user_profile: dict, candidates: list, intent: str) -> dict:
        """
        Batch analyzes strategic fit.
        Migrated from GeminiArchitect to use shared Provider.
        """
        if not self.client: return {}

        
        
        # Construct Prompt
        prompt = f"""
        You are a Senior M&A Partner. Evaluate these potential {intent} candidates for {user_profile['ticker']} ({user_profile['name']}).
        
        Your Goal: Re-rank these based on TRUE strategic fit, beyond just financials.
        
        Candidates:
        {json.dumps([{
            'ticker': c.get('ticker'), 
            'name': c.get('name'), 
            'business': c.get('business_summary', '')[:200]
        } for c in candidates], indent=2)}
        
        RETURN JSON MAP ONLY:
        1. **Rationale Headline**: 8-12 words. Be SPECIFIC about product/asset overlay. Avoid generic buzzwords.
        2. **Fit Score**: 0-100. (How much does this move the needle strategically?).
        3. **Synergy Type**: (e.g. "Cost Synergy", "Revenue Synergy", "Market Expansion").
        4. **Risk Factor**: The #1 concrete reason this deal might fail.
        
        OUTPUT ONLY JSON Array:
        [
            {{
                "ticker": "XYZ",
                "rationale_headline": "...",
                "fit_score": 85,
                "synergy_type": "...",
                "risk_factor": "..."
            }}
        ]
        """
        
        try:
            logger.info("AI BATCH: Sending request to Gemini...")
            response = self.client.models.generate_content(
                model=self.MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            
            text = response.text
             # Clean Markdown wrappers
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            elif "```" in text: text = text.split("```")[1].split("```")[0]
            
            logger.info(f"AI BATCH: Raw response: {text[:100]}...") # Log start of response
            
            result_json = json.loads(text.strip())
            
            # Normalize keys just in case model deviates
            final_map = {}
            for item in result_json:
                t = item.get('ticker')
                if t:
                    final_map[t] = {
                        "ticker": t,
                        "rationale_headline": item.get('rationale_headline') or item.get('headline') or "AI Analysis Ready",
                        "fit_score": item.get('fit_score') or 50,
                        "synergy_type": item.get('synergy_type') or item.get('synergy') or "Strategic",
                        "risk_factor": item.get('risk_factor') or item.get('risk') or "Execution Risk"
                    }
            logger.info(f"AI BATCH: Success. Mapped {len(final_map)} items.")
            return final_map
            
        except Exception as e:
            logger.error(f"Deal Architect Batch Error: {e}")
            return {}

    def generate_live_deal_memo(self, user: dict, candidate: dict, intent: str, mandate_mode: str, metric_data: dict, macro: dict, headlines: str) -> dict:
        """
        Generates Deep IC Memo using Google Search.
        Migrated from GeminiArchitect.
        """
        if not self.client: 
            return {
                "html": "<div class='alert alert-warning'>AI Service Unavailable (Missing Key)</div>", 
                "verdict": {"status": "UNKNOWN"}
            }

        start_time = datetime.now()
        current_date_str = start_time.strftime("%B %d, %Y")
        
        scores = metric_data.get('scores', {})
        metrics = metric_data.get('metrics', {})
        macro = macro or {}
        
        # Ensure safe defaults for f-string
        tnx = macro.get('tnx', 'N/A')
        offer_ev = metrics.get('offer_ev', 0) or 0
        premium = metrics.get('premium_pct', 0)
        coverage = metrics.get('coverage_ratio', 0)
        leverage = metrics.get('pro_forma_leverage', 0)
        prob = scores.get('probability_score', 0)
        strat = scores.get('strategic_score', 0)
        feas = scores.get('feasibility_score', 0)
        
        
        # Determine Roles based on Intent
        is_sell_side = 'sell' in intent.lower() or 'divest' in intent.lower()
        is_merger = 'merger' in intent.lower()
        
        if is_sell_side:
            acquirer_str = f"{candidate.get('name')} ({candidate.get('ticker')})"
            target_str = f"{user.get('name')} ({user.get('ticker')})"
            scenario_label = "DIVESTITURE / SALE (User is Target)"
        elif is_merger:
            acquirer_str = f"{user.get('name')} + {candidate.get('name')}"
            target_str = "Combined Entity"
            scenario_label = "MERGER OF EQUALS"
        else:
            acquirer_str = f"{user.get('name')} ({user.get('ticker')})"
            target_str = f"{candidate.get('name')} ({candidate.get('ticker')})"
            scenario_label = "ACQUISITION (User is Acquirer)"

        prompt = f'''
        You are a Senior M&A Partner.
        DATE: {current_date_str}.
        
        Scenario: {scenario_label}
        - Acquirer / Surviving Entity: {acquirer_str}
        - Target / Asset: {target_str}
        - Intent: {intent}
        - Mandate: {mandate_mode}
        
        LIVE DATA:
        - Macro: 10Y Treasury: {tnx}%
        - Physics: Offer EV ${offer_ev/1e9:.1f}B | Premium {premium}% | Coverage {coverage}x | PF Lev {leverage}x
        - Scores: Prob {prob}% | Strategic {strat} | Feasibility {feas}
        - Headlines: {headlines}
        
        TASK:
        1) Search & Validate: Check last 30 days for major issues.
        2) Write Investment Committee memo (HTML):
           - Verdict: GO / NO-GO
           - Why Now?
           - Deal killers?
           - Claims & Sources: List 3 key claims with source names.
           
        OUTPUT JSON:
        {{
            "html": "<h3>Investment Committee Memo...</h3>...",
            "verdict": {{ "status": "GO", "confidence": "High", "reason": "..." }},
            "recency_audit": {{ "search_performed": true, "key_findings_count": 2, "time_anchor_verified": true }}
        }}
        '''
        
        try:
            # Enable Google Search for Freshness
            tools = [types.Tool(google_search=types.GoogleSearch())]
            
            response = self.client.models.generate_content(
                model=self.MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=tools,
                    response_mime_type="application/json",
                    temperature=0.4
                )
            )
            
            text = response.text
            # Robust Parsing
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            elif "```" in text: text = text.split("```")[1].split("```")[0]
            
            data_json = json.loads(text.strip())
            
            # Simple validation
            if "html" not in data_json: 
                data_json["html"] = f"<div class='alert alert-danger'>AI Format Error</div>"
            if "verdict" not in data_json: 
                data_json["verdict"] = {"status": "UNKNOWN"}
            
            # Enforce Recency Audit in Output
            if "recency_audit" not in data_json:
                 data_json["recency_audit"] = {"status": "Implicit", "details": "AI did not return audit data."}
                
            return data_json

        except Exception as e:
            logger.error(f"Deal Architect Memo Error: {e}")
            return {
                "html": f"<div class='alert alert-danger'>AI Analysis Failed: {str(e)}</div>", 
                "verdict": {"status": "ERROR"}
            }

# Singleton Instance
brief_service = GeminiBriefService()
