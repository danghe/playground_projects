from src.analysis.strategic_radar import scan_sector_audit
from app import app
import sys

def verify():
    print("--- 1. Backend Trend Engine Verification ---")
    data, heatmap, narrative = scan_sector_audit("Tech")
    
    if not heatmap:
        print("FAIL: No heatmap data returned")
    else:
        print(f"Heatmap Groups: {[h['sub_industry'] for h in heatmap]}")
        print("OK: Heatmap populated")
        
    if not narrative:
        print("FAIL: No narrative generated")
    else:
        print("Narrative Points:")
        for n in narrative:
            print(f"- {n}")
        print("OK: Narrative generated")

    print("\n--- 2. Frontend HTML Verification ---")
    tester = app.test_client()
    try:
        response = tester.get('/deal-radar?sector=Tech')
        
        if response.status_code != 200:
            print(f"FAILED: Status Code {response.status_code}")
            return
            
        html = response.data.decode('utf-8')
        
        checks = [
            "heatmap-container",
            "heatmap-tile",
            "Trend Narrative",
            "filterTable(",
            "data-sub-industry="
        ]
        
        for c in checks:
            if c in html:
                print(f"[OK] Found '{c}'")
            else:
                print(f"[FAIL] Missing '{c}'")
                
    except Exception as e:
        print(f"Frontend Error: {e}")

if __name__ == "__main__":
    verify()
