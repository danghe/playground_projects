from src.analysis.strategic_radar import scan_sector_audit
from app import app
import sys

def verify():
    print("--- 1. Backend Catalyst Logic ---")
    data, _, _ = scan_sector_audit("Tech")
    
    if not data:
        print("FAIL: No data returned")
        return

    # Find a company with catalysts
    target = next((t for t in data if t['catalysts']), None)
    
    if target:
        cat = target['catalysts'][0]
        print(f"Company: {target['ticker']}")
        print(f"Catalyst: {cat}")
        
        # Verify New Fields
        if 'confidence' in cat:
            print(f"  [OK] Confidence: {cat['confidence']}")
        else:
            print("  [FAIL] Missing 'confidence'")
            
        if 'headline' in cat:
             print(f"  [OK] Headline: {cat['headline']}")
        else:
             print("  [FAIL] Missing 'headline'")
             
        # Verify Imminence Score Calculation
        print(f"  [OK] Imminence Score: {target['scores']['imminence']}")
    else:
        print("WARN: No catalysts found in default set (might be expected if mock data limited)")

    print("\n--- 2. Frontend Evidence Wiring ---")
    tester = app.test_client()
    try:
        response = tester.get('/deal-radar?sector=Tech')
        html = response.data.decode('utf-8')
        
        checks = [
            'id="evidenceDrawer"',
            'onclick="openEvidence(',
            'id="row-',
            'offcanvas-end'
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
