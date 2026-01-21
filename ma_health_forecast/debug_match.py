
import sys
import os
sys.path.append(os.getcwd())

from src.analysis.profile_engine import build_user_profile
from src.analysis.matchmaker import MatchEngine

def debug_ssnc():
    print("--- Debugging SSNC Match Logic ---")
    
    # 1. Build SSNC Profile
    print("Fetching SSNC Profile...")
    ssnc = build_user_profile("SSNC")
    print(f"SSNC: Cap=${ssnc.market_cap/1e9:.2f}B, Cash=${ssnc.total_cash/1e9:.2f}B, Firepower=${ssnc.firepower/1e9:.2f}B")

    # 2. Build WIT Profile (manually or via engine)
    engine = MatchEngine()
    print("\nRun find_targets(SSNC)...")
    matches = engine.find_targets(ssnc, sector_focus="All", limit=50)
    
    found_wit = False
    for m in matches:
        if m.ticker == "WIT":
            found_wit = True
            print(f"\n[ALERT] Found WIT in matches!")
            print(f"WIT Cap: ${m.market_cap/1e9:.2f}B")
            print(f"Ratio (WIT/SSNC): {m.market_cap / ssnc.market_cap:.2f}")
            print(f"Score: {m.combined_rank_score}")
            print("Drivers:", [d.label for d in m.drivers])
            break
            
    if not found_wit:
        print("\n[SUCCESS] WIT was filtered out.")
        
    # Check BRK-B too just in case
    for m in matches:
        if m.ticker == "BRK-B":
            print(f"\n[ALERT] Found BRK-B in matches!")
            print(f"BRK-B Cap: ${m.market_cap/1e9:.2f}B")

if __name__ == "__main__":
    debug_ssnc()
