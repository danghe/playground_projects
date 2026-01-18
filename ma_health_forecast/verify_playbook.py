from src.analysis.playbook_engine import PlaybookEngine
from src.analysis.strategic_radar import scan_sector_audit
from app import app
import sys

def verify():
    print("--- 1. Engine Logic Test ---")
    # Test Scenario 1: Distressed
    market_distressed = {"vix": 35.0, "financing_window": "Closed"}
    sector_distressed = {"spi_breadth": 10.0}
    pb1 = PlaybookEngine.generate_playbook(market_distressed, sector_distressed)
    print(f"Scenario 1 (Distressed): {pb1['regime']}")
    if pb1['regime'] == "Crisis Defense":
        print("  [OK] Correctly identified Crisis Defense")
    else:
        print(f"  [FAIL] Expected Crisis Defense, got {pb1['regime']}")

    # Test Scenario 2: Boom
    market_boom = {"vix": 12.0, "financing_window": "Open"}
    sector_boom = {"spi_breadth": 5.0}
    pb2 = PlaybookEngine.generate_playbook(market_boom, sector_boom)
    print(f"Scenario 2 (Boom): {pb2['regime']}")
    if pb2['regime'] == "Aggressive Growth":
         print("  [OK] Correctly identified Aggressive Growth")
    else:
         print(f"  [FAIL] Expected Aggressive Growth, got {pb2['regime']}")

    print("\n--- 2. Integration Test (StrategicRadar) ---")
    data, heatmap, narrative, playbook = scan_sector_audit("Tech")
    print(f"Integration Result: {playbook['regime']}")
    if 'actions' in playbook and 'CEO' in playbook['actions']:
        print("  [OK] Playbook contains Actions for CEO")
    else:
        print("  [FAIL] Missing Actions object")

    print("\n--- 3. Frontend UI Wiring ---")
    tester = app.test_client()
    try:
        response = tester.get('/deal-radar?sector=Tech')
        html = response.data.decode('utf-8')
        
        checks = [
            'id="playbookModal"',
            'data-bs-target="#playbookModal"',
            'Strategy Room',
            'Theme:'
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
