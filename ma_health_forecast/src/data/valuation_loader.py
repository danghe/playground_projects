import pandas as pd
from src.data.fred_loader import FredLoader

def fetch_valuation_series(which: str = "sp500_pe") -> pd.Series:
    """
    Fetch valuation data.
    Uses S&P 500 Index (SP500) as a proxy for Market Valuation.
    """
    fred = FredLoader()
    # SPASTT01USM661N: Total Share Prices for All Shares for the United States (OECD)
    # Using this as a proxy for SP500 because FRED's SP500 series might be truncated in API
    series_id = "SPASTT01USM661N"
    
    try:
        data = fred.fetch_series(series_id, start="1990-01-01")
        data.name = "SP500"
        return data
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.Series(dtype=float)
