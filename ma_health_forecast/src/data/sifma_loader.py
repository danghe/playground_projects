import pandas as pd
from src.data.fred_loader import FredLoader

def fetch_sifma_series(which: str, cfg_path: str = "config/external_sources.yaml", prefer_cache: bool = True) -> pd.Series:
    """
    Fetch issuance/liquidity data.
    Uses Commercial and Industrial Loans (BUSLOANS) as a proxy for Deal Financing Availability.
    """
    fred = FredLoader()
    # BUSLOANS: Commercial and Industrial Loans, All Commercial Banks
    series_id = "BUSLOANS"
    
    try:
        data = fred.fetch_series(series_id)
        data.name = "BUSLOANS"
        return data
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.Series(dtype=float)
