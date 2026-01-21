import sys
import os

# Add project root to path
sys.path.append(r"d:\00Intralinks\M&A Forecast Project\ma_health_forecast_project\ma_health_forecast")

print("--- Step 1: verifying imports ---")
try:
    from src.analysis.gemini_architect import GeminiArchitect
    print("SUCCESS: Imported GeminiArchitect")
except ImportError as e:
    print(f"FAILURE: Could not import GeminiArchitect: {e}")
    sys.exit(1)

try:
    from src.analysis.gemini_deep_dive import analyze_company
    print("SUCCESS: Imported analyze_company")
except ImportError as e:
    print(f"FAILURE: Could not import analyze_company: {e}")
    sys.exit(1)

print("\n--- Step 2: Instantiating Architect ---")
try:
    architect = GeminiArchitect()
    print("SUCCESS: Instantiated GeminiArchitect")
    if architect.api_key:
        print("SUCCESS: API Key found.")
    else:
        print("WARNING: API Key NOT found.")
except Exception as e:
    print(f"FAILURE: Instantiation failed: {e}")

print("\n--- Verification Complete ---")
