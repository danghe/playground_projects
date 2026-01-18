import pandas as pd

def fetch_deal_counts(cfg_path: str = "config/external_sources.yaml", prefer_cache: bool = True) -> pd.Series:
    """
    Generate synthetic monthly deal count series for demonstration purposes.

    The series spans 120 months starting from January 2010 and uses a linear trend combined
    with seasonal fluctuations to simulate changes in M&A deal activity over time. Random
    noise with a fixed seed is added for reproducibility.

    Returns
    -------
    pandas.Series
        Monthly deal counts labelled as ``DEAL_COUNT``.
    """
    import numpy as np
    end_date = pd.Timestamp.now()
    idx = pd.date_range(start="2010-01-01", end=end_date, freq="ME")
    rng = np.random.default_rng(seed=67890)
    # Linear upward trend from 200 to 400 over 120 months
    trend = np.linspace(200, 400, len(idx))
    # Seasonal variation using sine wave between -30 and +30
    season = 30 * np.sin(np.linspace(0, 6 * np.pi, len(idx)))
    noise = rng.normal(loc=0, scale=10, size=len(idx))
    data = trend + season + noise
    return pd.Series(data.astype(int), index=idx, name="DEAL_COUNT")
