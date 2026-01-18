import pandas as pd

def winsorize_z(z: pd.Series, clip: float) -> pd.Series:
    return z.clip(lower=-clip, upper=clip)

def zscore_expanding(x: pd.Series) -> pd.Series:
    mu = x.expanding(min_periods=24).mean()
    sigma = x.expanding(min_periods=24).std(ddof=0)
    return (x - mu) / sigma

def normalize_series(x: pd.Series, method: str, window, clip_z: float) -> pd.Series:
    if method == "zscore":
        if window == "expanding":
            z = zscore_expanding(x)
        else:
            z = (x - x.rolling(window).mean()) / x.rolling(window).std(ddof=0)
        return winsorize_z(z, clip=clip_z)
    elif method == "minmax":
        if window == "expanding":
            minv = x.expanding(min_periods=24).min()
            maxv = x.expanding(min_periods=24).max()
        else:
            minv = x.rolling(window).min()
            maxv = x.rolling(window).max()
        return (x - minv) / (maxv - minv)
    else:
        raise ValueError("Unknown normalize method")
