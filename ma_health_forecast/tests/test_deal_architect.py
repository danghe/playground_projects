
import sys
import os
import json
from dataclasses import dataclass

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

from src.analysis.matchmaker import MatchEngine, MatchCandidate, MatchDriver
from src.analysis.profile_engine import UserProfile
from src.analysis.deal_architect_deep_dive import calculate_deal_physics

# Mock User Profile
def mock_user_profile():
    return UserProfile(
        ticker="CVS",
        name="CVS Health",
        sector="Healthcare",
        sub_industry="Health Care Services",
        market_cap=80e9,
        enterprise_value=120e9,
        revenue=300e9,
        ebitda=15e9,
        total_cash=10e9,
        total_debt=50e9,
        revenue_growth=0.04,
        gross_margin=0.15,
        firepower=15e9, # Cash + Borrowing
        leverage=3.3,
        strategy_tags=["Consolidator"],
        business_summary="Mock CVS Summary"
    )

def mock_target_profile(ticker, mcap, ev, rev, ebitda, sub_ind):
    return UserProfile(
        ticker=ticker,
        name=f"Target {ticker}",
        sector="Healthcare",
        sub_industry=sub_ind,
        market_cap=mcap,
        enterprise_value=ev,
        revenue=rev,
        ebitda=ebitda,
        total_cash=1e9,
        total_debt=2e9,
        revenue_growth=0.10,
        gross_margin=0.20,
        firepower=5e9,
        leverage=2.0,
        strategy_tags=["Target"],
        business_summary="Mock Target Summary"
    )

def test_matchmaker_logic():
    print("\n--- Testing Matchmaker Logic (Banker Gates) ---")
    engine = MatchEngine()
    user = mock_user_profile()
    
    # Mocking universe service for test
    # We will bypass find_matches and test logic directly or use a mock universe
    # Since find_matches relies on self.universe_svc, we might need to integration test or mock it.
    # For simplicity, let's test the 'Deep Dive' logic which is pure function first, 
    # and then try to run MatchEngine if environment allows (it connects to DB).
    # Assuming DB exists in this env.
    
    try:
        from src.data.universe_service import UniverseService
        svc = UniverseService()
        if not svc.universe:
            print("WARN: Universe empty, skipping full Matchmaker integration test.")
        else:
            print(f"Universe Size: {len(svc.universe)}")
            matches = engine.find_matches(user, "BUY", "Adjacency")
            print(f"Matches Found: {len(matches)}")
            if matches:
                 m = matches[0]
                 print(f"Top Match: {m.ticker} | Score: {m.overall_score}")
                 print(f"Drivers: {[d.label for d in m.drivers]}")
    except Exception as e:
        print(f"MatchEngine Test Failed (Env issue?): {e}")

def test_deal_physics():
    print("\n--- Testing Deal Physics (Deterministic) ---")
    user = mock_user_profile()
    
    # Case 1: Affordable Target
    t1 = mock_target_profile("OAK", 5e9, 6e9, 2e9, 500e6, "Health Care Services")
    # Deal: 6e9 * 1.25 = 7.5e9. User Cash 10e9. Direct Pay.
    intent = "BUY"
    res1 = calculate_deal_physics(user, t1, intent)
    print(f"Case 1 (Affordable): Feasibility={res1['scores']['feasibility_score']} (Exp: 100)")
    # print(res1)
    
    # Case 2: LBO Candidate
    # Deal: 20e9. User Cash 10e9. Need 10e9 Debt.
    # PF Debt: 50 + 2 + 10 = 62. PF EBITDA: 15 + 2 = 17. Lev = 3.6x.
    t2 = mock_target_profile("LBO", 15e9, 16e9, 5e9, 2e9, "Health Care Services")
    res2 = calculate_deal_physics(user, t2, intent)
    print(f"Case 2 (LBO): Feasibility={res2['scores']['feasibility_score']} (Exp: 80-100 check lev)")
    print(f"   PF Leverage: {res2['metrics']['pro_forma_leverage']}x")
    
    # Case 3: Whale (Too Big)
    # Deal: 100e9.
    t3 = mock_target_profile("WHALE", 80e9, 100e9, 20e9, 5e9, "Health Care Services")
    res3 = calculate_deal_physics(user, t3, intent)
    print(f"Case 3 (Whale): Feasibility={res3['scores']['feasibility_score']} (Exp: <50)")
    print(f"   PF Leverage: {res3['metrics']['pro_forma_leverage']}x")

if __name__ == "__main__":
    test_deal_physics()
    test_matchmaker_logic()
