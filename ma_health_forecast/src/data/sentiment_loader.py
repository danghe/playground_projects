import pandas as pd
from src.data.fred_loader import FredLoader

def fetch_sentiment_series(which: str = "ceo_confidence") -> pd.Series:
    """
    Fetch sentiment data. 
    Uses OECD Business Confidence Index (BSCICP03USM665S) as a proxy for CEO Confidence.
    """
    fred = FredLoader()
    # BSCICP03USM665S: OECD Standardized Business Confidence Indicator for United States
    series_id = "BSCICP03USM665S"
    
    try:
        data = fred.fetch_series(series_id, start="1990-01-01")
        data.name = "BUSINESS_CONFIDENCE"
        
        # Forward fill to present if data is lagged (OECD data often is)
        # We resample to monthly to ensure we have a grid, then ffill
        data = data.resample("ME").ffill()
        
        return data
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.Series(dtype=float)
