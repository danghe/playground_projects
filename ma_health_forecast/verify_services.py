import sys
import os
import json

# Add project root to path
sys.path.append(r"d:\00Intralinks\M&A Forecast Project\ma_health_forecast_project\ma_health_forecast")
from dotenv import load_dotenv
load_dotenv()

print("--- Step 1: Testing Brief Service ---")
try:
    from src.analysis.gemini_brief import brief_service
    print(f"Service instantiated. Models: {brief_service.MODELS}")
    
    if os.getenv("GEMINI_API_KEY"):
        print("API Key present.")
    else:
        print("WARNING: API Key missing in environment.")

    # Mock call to _generate_content_robust (without making real API call if possible, or just checking method existence)
    if hasattr(brief_service, '_generate_content_robust'):
        print("SUCCESS: _generate_content_robust method exists.")
    else:
        print("FAILURE: _generate_content_robust method MISSING.")
        sys.exit(1)

except ImportError as e:
    print(f"FAILURE: Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FAILURE: Generic error: {e}")
    sys.exit(1)

print("\n--- Step 2: Testing Deep Dive Service ---")
try:
    from src.analysis.gemini_deep_dive import analyze_company
    # Provide dummy args
    res = analyze_company("TEST", "radar_target", {"name": "Test Co", "sector": "Tech", "drivers": "None"})
    if "AI Analysis unavailable" in res and "All models failed" not in res:
         # Likely API key missing or network error but logic ran
         print(f"Result (Expected Error/Success): {res[:50]}...")
    elif "All models failed" in res:
         print("WARNING: 'All models failed' returned. Check API Key or Quota.")
    else:
         print(f"Result (Success?): {res[:50]}...")
         
except Exception as e:
    print(f"FAILURE: Deep dive error: {e}")

print("\n--- Verification Complete ---")
