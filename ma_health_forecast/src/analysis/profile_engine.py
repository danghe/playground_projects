from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
import random
import yfinance as yf
from src.data.universe_service import UniverseService

@dataclass
class UserProfile:
    """
    Rich profile of the User's company (The 'Client').
    Includes Financials, Trust Labels, and Derived Strategic Tags.
    """
    ticker: str
    name: str
    sector: str
    sub_industry: str
    
    # Financials (USD)
    market_cap: float
    enterprise_value: Optional[float]
    total_cash: float
    total_debt: float
    ebitda: float
    revenue: float
    revenue_growth: float  # 0.05 = 5%
    gross_margin: float    # 0.40 = 40%
    
    # Derived Metrics
    firepower: float       # Cash + 3*EBITDA - Debt
    leverage: float        # Debt / EBITDA
    
    # Strategic Context
    business_summary: str
    strategy_tags: List[str] = field(default_factory=list)
    
    # Audit / Trust
    currency: str = "USD"
    warnings: List[str] = field(default_factory=list)
    as_of: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_financial_summary(self) -> str:
        """Returns a concise string for AI prompting."""
        fp_str = f"${self.firepower/1e9:.1f}B" if self.firepower > 1e9 else f"${self.firepower/1e6:.1f}M"
        lev_str = f"{self.leverage:.1f}x" if self.leverage is not None else "N/A"
        growth = f"{self.revenue_growth*100:.1f}%" if self.revenue_growth is not None else "N/A"
        margin = f"{self.gross_margin*100:.1f}%" if self.gross_margin is not None else "N/A"
        
        return (f"Firepower: {fp_str} | Leverage: {lev_str} | "
                f"Growth: {growth} | Margin: {margin}")

def _fetch_with_retry(ticker: str, retries: int = 3) -> Optional[dict]:
    """Robust yfinance fetch with backoff."""
    for i in range(retries):
        try:
            if i > 0:
                time.sleep((2 ** i) + random.uniform(0, 1))
                
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # fast_info fallback for some fields if needed, 
            # but usually info covers essentials for deep dive.
            if info and info.get('regularMarketPrice'):
                return info
        except Exception as e:
            print(f"[ProfileEngine] Retry {i+1} for {ticker} failed: {e}")
            continue
            
    return None

def build_user_profile(ticker: str) -> UserProfile:
    """
    Builds a realtime UserProfile from yfinance (Live).
    Calculates Firepower and Strategic Tags on the fly.
    """
    # 0. Normalize
    ticker = ticker.strip().upper()
    
    # 1. Fetch Live Data
    info = _fetch_with_retry(ticker)
    if not info:
        # Return a "Hollow" profile with warnings
        return UserProfile(
            ticker=ticker, name=ticker, sector="Unknown", sub_industry="Unknown",
            market_cap=0, enterprise_value=0, total_cash=0, total_debt=0, ebitda=0,
            revenue=0, revenue_growth=0, gross_margin=0, firepower=0, leverage=0,
            business_summary="Data Unavailable", warnings=["Failed to fetch live data from yfinance."]
        )
        
    # 2. Extract Fields (Safe Parsing)
    def _get(k, default=0.0):
        v = info.get(k)
        return float(v) if v is not None else default

    name = info.get('shortName') or info.get('longName') or ticker
    sector = info.get('sector', 'Unknown')
    industry = info.get('industry', 'Unknown')
    summary = info.get('longBusinessSummary') or info.get('city') or "No description."
    
    mcap = _get('marketCap')
    ev = _get('enterpriseValue')
    cash = _get('totalCash')
    debt = _get('totalDebt')
    ebitda = _get('ebitda')
    rev = _get('totalRevenue')
    rev_growth = _get('revenueGrowth')
    gross_margin = _get('grossMargins')
    
    # 3. Compute Derived Metrics
    # Firepower = Cash + (3.0 * EBITDA) - Debt (Standard PE Proxy)
    # If EBITDA is negative, we assume 0 borrowing capacity on earnings.
    borrowing_capacity = max(0, 3.0 * ebitda)
    firepower = cash + borrowing_capacity - debt
    
    # Leverage = Debt / EBITDA
    leverage = debt / ebitda if ebitda > 1000 else 99.0  # High if no earnings
    
    # 4. Strategic Tags
    tags = []
    
    # Tag: Growth Stalled
    if rev_growth < 0.05:
        tags.append("Growth Stalled")
        
    # Tag: Margin Expansion Needed (Sector Benchmarking)
    universe_svc = UniverseService()
    sector_peers = universe_svc.get_tickers(sector=sector, limit=100)
    
    if len(sector_peers) > 5 and gross_margin > 0:
        # Calculate Sector Avg Margin
        # Note: This relies on Universe Store data which might be latched. 
        # Ideally we'd use live, but that's too slow for 100 peers.
        # We accept the 'Reference Data' comes from the trusted DB.
        
        peer_margins = []
        for p_ticker in sector_peers:
            p_data = universe_svc.get_company(p_ticker)
            if p_data:
                # Some store data might keep margin in different keys or not have it.
                # Just checking 'grossMargins' if present in fundamentals, else skip
                # Standard store structure for fundamentals includes raw yfinance keys often.
                m = p_data.get('grossMargins') or p_data.get('gross_margin')
                if m: peer_margins.append(float(m))
        
        if peer_margins:
            avg_margin = sum(peer_margins) / len(peer_margins)
            if gross_margin < (avg_margin - 0.05): # 5% below peer avg
                tags.append("Margin Expansion Needed")
    
    return UserProfile(
        ticker=ticker,
        name=name,
        sector=sector,
        sub_industry=industry,
        market_cap=mcap,
        enterprise_value=ev,
        total_cash=cash,
        total_debt=debt,
        ebitda=ebitda,
        revenue=rev,
        revenue_growth=rev_growth,
        gross_margin=gross_margin,
        firepower=firepower,
        leverage=leverage,
        business_summary=summary,
        strategy_tags=tags,
        warnings=[]
    )

def build_user_profile_live(ticker: str) -> UserProfile:
    """
    Alias for build_user_profile to satisfy the new interface requirement.
    The existing build_user_profile ALREADY fetches live data via _fetch_with_retry -> yf.Ticker(ticker).info.
    """
    return build_user_profile(ticker)

