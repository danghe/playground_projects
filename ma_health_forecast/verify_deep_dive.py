
import json
import sys
import os
from app import app
from src.analysis.gemini_deep_dive import analyze_company

def test_deep_dive_integration():
    print("Testing Deep Dive Integration...")
    
    # 1. Check Endpoint Registration
    client = app.test_client()
    with app.app_context():
        # Mock the AI call to avoid actual cost/latency during quick verify, 
        # or we can let it fail gracefully if no key.
        # But we want to ensure the plumbing works.
        
        payload = {
            "ticker": "TEST",
            "type": "buyer",
            "context": {"name": "Test Corp", "sector": "Tech"}
        }
        
        # We can't easily mock genai without installed libraries or patching.
        # So we'll hit the endpoint and expect either a success (html) or a handled error.
        # If API key is missing, it returns error HTML.
        
        try:
            r = client.post('/api/v2/deep-dive', json=payload)
            if r.status_code == 200:
                data = json.loads(r.data)
                if 'html' in data:
                    print(f"SUCCESS: Endpoint returned HTML (Length: {len(data['html'])})")
                    # It might be an error message HTML, but that's valid flow.
                    if "Error" in data['html'] or "unavailable" in data['html']:
                        print("NOTE: AI returned error message (expected if no key/model issue), but flow handled it.")
                    else:
                        print("NOTE: Real AI response received.")
                else:
                    print("FAILED: No 'html' key in response")
                    return False
            else:
                print(f"FAILED: Status Code {r.status_code}")
                return False
                
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    # 2. Check File Existence
    if not os.path.exists("src/analysis/gemini_deep_dive.py"):
        print("FAILED: src/analysis/gemini_deep_dive.py not found")
        return False
        
    print("ALL CHECKS PASSED")
    return True

if __name__ == "__main__":
    if test_deep_dive_integration():
        sys.exit(0)
    else:
        sys.exit(1)
