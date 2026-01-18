from app import app
from src.analysis.strategic_radar import scan_sector_audit
import sys

def verify():
    print("--- 1. Backend Verification (SPI & Data) ---")
    data = scan_sector_audit("Tech")
    if not data:
        print("FAIL: No data returned from scan_sector_audit")
    else:
        first = data[0]
        print(f"Ticker: {first['ticker']}")
        print(f"SPI Score: {first['scores']['spi']}")
        
        # Verify Components
        comps = first['evidence'].get('components')
        if comps:
            print(f"SPI Components: {comps}")
            if 'governance' in comps and 'strategic' in comps:
                print("OK: SPI 5-Component Structure Verified")
            else:
                print("FAIL: Components missing keys")
        else:
            print("FAIL: SPI Components missing dictionary")
            
        print(f"Data Source: {first['evidence'].get('data_source', 'N/A')}")

    print("\n--- 2. Frontend Verification (HTML) ---")
    tester = app.test_client()
    try:
        response = tester.get('/deal-radar?sector=Tech')
        
        if response.status_code != 200:
            print(f"FAILED: Status Code {response.status_code}")
            return
            
        html = response.data.decode('utf-8')
        
        # Checks
        checks = [
            "Seller Pressure Index (SPI)", # Tooltip Header
            "Price Stress:", # New Tooltip Row
            "Earnings:", 
            "Balance Sheet:",
            "Governance:",
            "Strategic:"
        ]
        
        for c in checks:
            if c in html:
                print(f"[OK] Found '{c}'")
            else:
                print(f"[FAIL] Missing '{c}' in HTML")
                
    except Exception as e:
        print(f"Frontend Error: {e}")

if __name__ == "__main__":
    verify()
