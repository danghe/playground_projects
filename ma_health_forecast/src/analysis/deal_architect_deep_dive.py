import yfinance as yf
from datetime import datetime
from src.analysis.profile_engine import build_user_profile_live, UserProfile
from src.analysis.gemini_architect import GeminiArchitect
from src.data.universe_service import UniverseService

def fetch_macro_context() -> dict:
    """Fetches ^TNX (10-year yield) as macro anchor."""
    try:
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="1d")
        if not hist.empty:
            rate = hist['Close'].iloc[-1]
            return {"tnx": round(rate, 2)}
    except:
        pass
    return {"tnx": 4.0} # Fallback

def fetch_headlines(ticker: str, limit: int = 5) -> str:
    """Fetches top news headlines via yfinance."""
    try:
        t = yf.Ticker(ticker)
        news = t.news
        headlines = []
        for n in news[:limit]:
            title = n.get('title', '')
            pub = n.get('providerPublishTime', 0)
            date_str = datetime.fromtimestamp(pub).strftime('%Y-%m-%d')
            headlines.append(f"- {date_str}: {title}")
        return "\n".join(headlines)
    except:
        return "No recent news found via yfinance."

def calculate_deal_physics(user: UserProfile, cand: UserProfile, intent: str) -> dict:
    """
    Deterministic Deal Physics & Feasibility Scoring.
    Returns dictionary of scores and calculated metrics.
    """
    scores = {}
    
    # --- 1. Deal Math ---
    cand_ev = cand.enterprise_value if cand.enterprise_value > 0 else cand.market_cap
    premium_assumed = 0.25 if intent == "BUY" else 0.30 if intent == "SELL" else 0.10
    offer_ev = cand_ev * (1 + premium_assumed)
    
    candidate_firepower = cand.firepower # Not used directly in coverage but good to have
    
    # Financial Capacity (Banker Style)
    # 1. Total Capacity = Cash + Debt Capacity (4.5x) + Stock Capacity (20%)
    debt_cap = max(0, (4.5 * user.ebitda) - user.total_debt)
    stock_cap = user.market_cap * 0.20
    user_total_capacity = user.total_cash + debt_cap + stock_cap
    
    # Coverage: Total Capacity / Offer EV
    coverage = user_total_capacity / offer_ev if offer_ev > 0 else 0
    
    # Pro-Forma Leverage (Simulated LBO)
    pf_leverage = 99.0
    combined_ebitda = user.ebitda + cand.ebitda
    if combined_ebitda > 0:
        new_debt = max(0, offer_ev - user.total_cash)
        pf_debt = user.total_debt + cand.total_debt + new_debt
        pf_leverage = pf_debt / combined_ebitda
    
    # --- 2. Scores & Verdict (Upgrade A: Consistent Policy) ---
    
    # Defaults
    score_feas = 50.0
    verdict = "REVIEW"
    feasibility_drivers = []
    structure_options = []
    
    # Caps & Logic per Intent
    is_breach = False
    
    # Calculate Leverage Band
    lev_band = "OK"
    if pf_leverage > 4.5: lev_band = "BREACH"
    elif pf_leverage > 4.0: lev_band = "TIGHT"
    
    if intent == "BUY":
        if pf_leverage > 4.5 and coverage < 1.0:
            is_breach = True
            score_feas = 30
            verdict = "NO-GO"
            feasibility_drivers.append(f"PF Leverage {pf_leverage:.1f}x > 4.5x Cap")
            
            # Generate Structure Option (Upgrade A)
            # Try to fix by using stock?
            # Reduce Debt needed by increasing Equity contribution?
            # Or just show the gap.
            gap = new_debt - (4.5 * combined_ebitda - cand.total_debt - user.total_debt)
            if gap > 0:
                structure_options.append({
                    "name": "Deleveraging Mix",
                    "desc": f"Reduce Cash offer or add Stock component to lower debt by ${gap/1e6:.0f}M.",
                    "impact": "Lowers PF Leverage to 4.5x"
                })
        elif pf_leverage <= 4.5:
            score_feas = 100 if coverage > 1.0 else (70 + (4.5 - pf_leverage)*10)
            verdict = "GO"
            
    elif intent == "SELL":
        # Acquirer logic: passed gate?
        score_feas = 90
        verdict = "GO"
        
    elif intent == "MERGE":
        if pf_leverage > 4.0:
            is_breach = True
            score_feas = 40
            verdict = "NO-GO"
            feasibility_drivers.append(f"PF Lev {pf_leverage:.1f}x > 4.0x Cap")
        else:
            score_feas = 80
            verdict = "GO"

    # Drivers Metadata
    rate_sens = "HIGH" if max(0, pf_leverage) > 3.0 else "MED"
    feas_drivers_meta = {
        "cash_coverage": f"{coverage:.2f}x",
        "pf_leverage_band": lev_band,
        "rate_sensitivity": rate_sens,
        "breach_details": feasibility_drivers
    }

    scores['feasibility_score'] = min(100, max(0, score_feas))
    
    # Strategic Fit Score (Simple Proxies)
    fit_score = 50
    if user.sub_industry == cand.sub_industry: fit_score += 30
    elif user.sector == cand.sector: fit_score += 15
    
    if cand.revenue_growth > user.revenue_growth: fit_score += 10 # Growth injection
    if intent == "MERGE" and (0.5 <= (cand.market_cap / user.market_cap) <= 1.5): fit_score += 20
    
    fit_score = min(100, fit_score)
    scores['strategic_score'] = fit_score
    
    # Close Probability Breakdown (Upgrade B)
    # 1. Financing (Feasibility Map)
    fin_score = scores['feasibility_score']
    
    # 2. Regulatory
    combined_rev = user.revenue + cand.revenue
    reg_score = 70
    if combined_rev > 20e9 and cand.sub_industry == user.sub_industry:
        reg_score = 40
    
    # 3. Willingness (Check SPI/BR from Universe Service)
    will_score = 50
    will_status = "Unknown"
    
    # Try to fetch real SPI/BR since live profile is just yfinance
    try:
        svc = UniverseService()
        stored_cand = svc.get_company(cand.ticker)
        if stored_cand:
            if intent == "BUY":
                if stored_cand.get('spi_score'):
                    spi = stored_cand['spi_score']
                    will_status = "Explicit (SPI)"
                    will_score = 85 if spi > 60 else (60 if spi > 30 else 35)
            elif intent == "SELL":
                 # Candidate is Acquirer here (Logic inversion caution: 'cand' arg is 'cand_ticker')
                 # perform_live_dossier passes cand_ticker correct
                 if stored_cand.get('buyer_readiness'):
                     will_status = "Explicit (Readiness)"
                     will_score = stored_cand['buyer_readiness']
    except:
        pass # Fallback to 50
        
    prob_score = (fin_score * 0.4) + (reg_score * 0.25) + (will_score * 0.35)
    
    scores['probability_score'] = int(prob_score) # List view legacy
    scores['close_probability'] = int(prob_score)
    scores['financing_score'] = int(fin_score)
    scores['regulatory_score'] = int(reg_score)
    scores['willingness_score'] = int(will_score)
    
    
    # --- Payload ---
    return {
        "scores": scores,
        "metrics": {
            "offer_ev": offer_ev,
            "premium_pct": premium_assumed * 100,
            "coverage_ratio": round(coverage, 2),
            "pro_forma_leverage": round(pf_leverage, 1),
            "combined_revenue": combined_rev,
            "total_capacity": user_total_capacity,
            "feasibility_drivers": feas_drivers_meta,
            "structure_options": structure_options
        },
        "verdict_data": {
            "status": verdict,
            "reason": "Leverage Breach" if is_breach else "Financially Feasible"
        },
        "willingness_status": will_status
    }

def perform_live_dossier(user_ticker: str, cand_ticker: str, intent: str, mandate_mode: str = "Consolidation") -> dict:
    """
    Orchestrator: Live Fetch -> Deterministic Deal Physics.
    Refactored to return raw data for Controller-level AI generation.
    """
    # 1. Live Fetch (Enforced)
    user = build_user_profile_live(user_ticker)
    cand = build_user_profile_live(cand_ticker)
    
    # 2. Context
    macro = fetch_macro_context()
    metric_data = calculate_deal_physics(user, cand, intent)
    
    headlines_str = fetch_headlines(cand_ticker)
    
    # 3. Return Data Bundle
    return {
        "user": user.__dict__,
        "candidate": cand.__dict__,
        "metrics": metric_data['metrics'],
        "scores": metric_data['scores'],
        "macro": macro,
        "headlines": headlines_str,
        "timestamp": datetime.now().isoformat()
    }

