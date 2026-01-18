import pandas as pd

def fetch_ipo_counts(cfg_path: str = "config/external_sources.yaml", prefer_cache: bool = True) -> pd.Series:
    """
    Generate synthetic monthly IPO count series for demonstration purposes.

    The series spans 120 months starting from January 2010 and uses a simple sinusoidal
    pattern with added noise to simulate varying IPO activity over time. Using a fixed
    seed ensures reproducibility.

    Returns
    -------
    pandas.Series
        Monthly IPO counts labelled as ``IPO_COUNT``.
    """
    import numpy as np
    # Create monthly date index
    end_date = pd.Timestamp.now()
    idx = pd.date_range(start="2010-01-01", end=end_date, freq="ME")
    # Generate synthetic IPO count data
    # base sinusoidal variation between 5 and 20
    # Add random noise with fixed seed for reproducibility
    rng = np.random.default_rng(seed=12345)
    sine_wave = 10 + 5 * np.sin(np.linspace(0, 4 * np.pi, len(idx)))
    noise = rng.normal(loc=0, scale=2, size=len(idx))
    data = (sine_wave + noise).clip(min=1)  # ensure positive counts
    return pd.Series(data.astype(int), index=idx, name="IPO_COUNT")
