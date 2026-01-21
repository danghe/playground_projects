
import os
from google import genai
from google.genai import types
from datetime import datetime
import json

class MetricAIClient:
    """
    Centralized Gemini wrapper for Deal Architect v1.1.
    Uses google.genai (v1.0+) SDK to support Gemini 3.0 Flash.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricAIClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("WARN: GEMINI_API_KEY not found. AI features disabled.")
            self.client = None
            return

        try:
            # New SDK Initialization
            self.client = genai.Client(api_key=self.api_key)
            print("AI Client initialized successfully (Gemini 3.0 Ready).")
        except Exception as e:
            print(f"Error initializing AI Client: {e}")
            self.client = None

    def generate_content(self, prompt: str, mode: str = "batch", use_search: bool = False, json_mode: bool = False) -> str:
        """
        Wrapper for generate_content enforcing Gemini 3.0 Flash.
        """
        if not self.client:
            return ""

        # Enforce User Requirement: Gemini 3.0 Flash
        target_model = "gemini-3.0-flash-preview" 

        try:
            # Config construction for New SDK
            config_args = {
                "response_mime_type": "application/json" if json_mode else "text/plain",
                "temperature": 0.2 if mode == "batch" else 0.4
            }
            
            # Tools
            if use_search:
                config_args["tools"] = [{"google_search": {}}]

            response = self.client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_args)
            )
            
            if not response.text:
                return ""
                
            return response.text

        except Exception as e:
            print(f"AI Generation Error ({mode}) on {target_model}: {e}")
            return ""

ai_client = MetricAIClient()
