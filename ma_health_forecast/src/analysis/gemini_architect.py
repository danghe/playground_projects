import os
import json
from google import genai
from google.genai import types

class GeminiArchitect:
    """
    AI Architect for Deal Matching.
    Uses Google's Gemini models to provide strategic rationales for M&A matches.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found. AI features will be disabled.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        # Cascading Model Strategy (Aligned with llm_forecast.py)
        # 1. Gemini 3.0 Pro (Best Reasoning)
        # 2. Gemini 3.0 Flash (Fast/Efficient)
        # 3. Gemini 2.0 Flash (Stable Fallback)
        # 4. Gemini 1.5 Pro (Legacy Stable)
        self.models_to_try = [
            'gemini-3-pro-preview',
            'gemini-3-flash-preview',
            'gemini-2.0-flash-exp',
            'gemini-1.5-pro',
        ]

    def analyze_match_batch(self, user_profile: dict, matches: list, intent: str) -> dict:
        """
        Analyzes a batch of matches and returns a dictionary of strategic rationales.
        
        Args:
            user_profile: Dict containing user's profile (name, sector, description, etc.)
            matches: List of match dictionaries (must contain 'ticker', 'name', 'description')
            intent: 'BUY', 'SELL', or 'MERGE'
        
        Returns:
            Dict[str, str]: Mapping of Ticker -> HTML Rationale
        """
        if not self.client or not matches:
            return {}

        # 1. Construct the Batch Prompt
        candidates_str = ""
        for m in matches:
            candidates_str += f"- {m.get('ticker')} ({m.get('name')}): {m.get('description', 'No description')} [Sector: {m.get('sector')}]\n"

        prompt = f"""
        **Role**: Top-tier M&A Investment Banker.
        **Task**: Provide a "One-Line Strategic Hook" for each of the following targets, specifically for the client below.
        
        **CLIENT (The {intent}ER)**:
        - Name: {user_profile.get('name')} ({user_profile.get('ticker')})
        - Sector: {user_profile.get('sector')}
        - Business: {user_profile.get('description')}
        
        **CANDIDATES**:
        {candidates_str}
        
        **INSTRUCTIONS**:
        - for each candidate, write a concise, punchy 1-sentence strategic rationale (max 20 words).
        - Focus on *synergy*, *market consolidation*, or *tech acquisition*.
        - **Format**: Return ONLY valid JSON mapping Ticker -> Rationale String.
        
        **EXAMPLE JSON**:
        {{
            "AAPL": "Ideal strategic fit to expand consumer hardware ecosystem.",
            "MSFT": "Transformative merger potential to dominate enterprise cloud."
        }}
        """

        # 2. Execute with Model Cascade
        for model_name in self.models_to_try:
            try:
                print(f"=== [Gemini Architect] Proposing Matches with {model_name} ===", flush=True)
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                text = response.text
                
                # Check coverage
                if not text:
                    raise ValueError("Empty response from model")

                # Parse JSON
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    # Fallback cleanup
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    data = json.loads(text)
                
                print(f"> Success: Parsed rationales for {len(data)} items.", flush=True)
                return data

            except Exception as e:
                print(f"> WARNING: Model {model_name} failed: {e}", flush=True)
                continue

        print("> ERROR: All models failed to generate rationales.", flush=True)
        return {}
