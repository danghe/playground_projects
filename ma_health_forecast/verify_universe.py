from src.data.universe_service import UniverseService
import sys

def verify():
    print("--- Verifying Universe Service ---")
    u = UniverseService()
    
    stats = u.get_stats()
    print(f"Universe Stats: {stats}")
    
    print("-" * 20)
    gaming_tickers = u.get_tickers(sub_industry="Electronic Gaming & Multimedia")
    print(f"Gaming Tickers ({len(gaming_tickers)}): {gaming_tickers}")
    
    if len(gaming_tickers) < 3:
        print("FAIL: Gaming tickers count too low (Expected >= 3)")
    else:
        print("OK: Gaming universe populated")
        
    print("-" * 20)
    company = u.get_company("AAPL")
    if company:
        print(f"Metadata for AAPL: {company}")
        if company.get('sector') == 'Tech':
            print("OK: AAPL is Tech")
        else:
            print(f"FAIL: AAPL sector is {company.get('sector')}")
    else:
        print("WARN: AAPL not found in universe yet")

if __name__ == "__main__":
    verify()
