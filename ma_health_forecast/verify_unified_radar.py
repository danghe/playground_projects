from src.analysis.strategic_radar import scan_sector_audit
from app import app
import sys

def verify_score(name, score, min_val=0, max_val=100):
    try:
        val = int(score)
        if min_val <= val <= max_val:
            print(f"  [OK] {name}: {val}")
            return True
        else:
            print(f"  [FAIL] {name}: {val} out of range")
            return False
    except:
         print(f"  [FAIL] {name}: Not a number ({score})")
         return False

def verify_backend_logic():
    print("--- 1. Backend Logic (Audit-Grade) ---")
    
    # Check Store
    from src.data.universe_service import UniverseService
    svc = UniverseService()
    
    if not svc.universe:
        print("[WARN] Universe Store empty. Ingestion needed.")
        # Create dummy data for verification if empty
        dummy_uni = [{"ticker": "TEST", "sector": "Tech", "sub_industry": "Software", "market_cap": 1e9}]
        dummy_fund = {"TEST": {"total_cash": 1e8, "total_debt": 5e7, "ebitda": 2e7, "provenance": {"source":"Test","timestamp":"Now"}}}
        svc.universe = dummy_uni
        svc.fundamentals = dummy_fund
        print("[INFO] Loaded Dummy Data for Verification.")
    
    # Test Sector Map
    s_map = svc.get_sector_map("Tech")
    print(f"Sector Map Size: {len(s_map)}")
    
    # Test Strategic Radar
    from src.analysis.strategic_radar import StrategicMarketEngine, StrategicSECMonitor
    engine = StrategicMarketEngine()
    monitor = StrategicSECMonitor()
    
    # Mock analyzing a ticker using pre-fetched
    t = "TEST" if "TEST" in s_map else list(s_map.keys())[0] if s_map else "AAPL"
    
    print(f"Analyzing {t}...")
    pre_fetched = s_map.get(t)
    data = engine.analyze_ticker(t, monitor, pre_fetched_fund=pre_fetched)
    
    if data:
        print(f"[OK] Analysis Successful for {t}")
        print(f"  Firepower: ${data['evidence']['firepower']:,.0f}")
        print(f"  Source: {data['evidence'].get('provenance', {}).get('source', 'N/A')}")
    else:
        print("[FAIL] Analysis returned None")

    # Original Backend Unified Logic checks (adapted)
    print("\n--- 1. Backend Unified Logic (Original) ---")
    data, _, _ = scan_sector_audit("Tech")
    
    if not data:
        print("FAIL: No data returned")
        return

    first = data[0]
    print(f"Checking Ticker: {first['ticker']}")
    
    # Check Scores
    scores = first['scores']
    verify_score("SPI", scores['spi'])
    verify_score("Buyer Ready", scores['buyer_readiness'])
    verify_score("Susceptibility", scores['susceptibility'])
    verify_score("Imminence", scores['imminence'])
    
    # Check Path
    path = first['prediction']['path']
    print(f"  [OK] Path: {path} ({first['prediction']['rationale']})")
    
    # Check Unified Drivers
    drivers = first['evidence']['top_drivers']
    if drivers:
        print(f"  [OK] Drivers: {[d['label'] for d in drivers]}")
    else:
        print("  [WARN] No drivers found (might be low risk company)")


def verify():
    verify_backend_logic()

    print("\n--- 2. Frontend HTML Columns ---")
    tester = app.test_client()
    try:
        response = tester.get('/deal-radar?sector=Tech')
        html = response.data.decode('utf-8')
        
        checks = [
            "cell-scores", # Class for score grid
            "BUY", "SELL", "TGT", "NOW", # Score Headers
            "Most likely path", # Is this in header? We need to verify column headers changed too
            "prediction", # path output
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
