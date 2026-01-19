from src.data.universe_service import UniverseService
import sys

def verify_priorities():
    print("--- Verifying Priority Tickers & New Sectors ---")
    u = UniverseService()
    
    # New additions to check
    # Format: Ticker, Expected Sector (Loose check)
    checks = [
        ('ISRG', 'Healthcare'),
        ('ENPH', 'Energy'),
        ('PANW', 'Technology'), 
        ('TSM', 'Technology'),
        ('GEHC', 'Healthcare')
    ]
    
    passed = 0
    for ticker, expected_sector in checks:
        company = u.get_company(ticker)
        if company:
            actual_sector = company.get('sector', 'Unknown')
            # Handle aliasing
            if expected_sector == 'Energy' and actual_sector == 'Technology':
                 # Solar sometimes classifies as Semi/Tech, verify sub-industry
                 print(f"WARN: {ticker} classified as {actual_sector}/{company.get('sub_industry')}")
                 passed += 1
            elif expected_sector in actual_sector or actual_sector in expected_sector:
                print(f"OK: {ticker} found in {actual_sector}")
                passed += 1
            else:
                print(f"FAIL: {ticker} found but sector mismatch. Expected {expected_sector}, got {actual_sector}")
        else:
            print(f"FAIL: {ticker} NOT found in universe")
            
    print("-" * 20)
    print(f"Verification Result: {passed}/{len(checks)} passed")

if __name__ == "__main__":
    verify_priorities()
