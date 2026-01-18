import pandas as pd

def get_regime(value: float) -> str:
    if value >= 60:
        return "Robust Expansion"
    elif value >= 50:
        return "Moderate Expansion"
    elif value >= 40:
        return "Cooling / Neutral"
    else:
        return "Contraction"

def generate_executive_summary(df: pd.DataFrame, fc: pd.DataFrame) -> str:
    """
    Generate a text summary for the CEO.
    """
    latest = df.iloc[-1]
    prev_month = df.iloc[-2]
    yoy = df.iloc[-13] if len(df) > 12 else df.iloc[0]
    
    current_val = latest["Composite"]
    change_mom = current_val - prev_month["Composite"]
    change_yoy = current_val - yoy["Composite"]
    
    regime = get_regime(current_val)
    
    # Forecast outlook
    fc_end_val = fc["forecast"].iloc[-1]
    fc_trend = "improving" if fc_end_val > current_val else "softening"
    
    # Drivers
    buckets = [c for c in df.columns if c.startswith("BKT_")]
    drivers = latest[buckets].sort_values(ascending=False)
    top_driver = drivers.index[0].replace("BKT_", "").replace("_", " ").title()
    lag_driver = drivers.index[-1].replace("BKT_", "").replace("_", " ").title()
    
    summary = f"""
    <h3>Executive Summary</h3>
    <p>The M&A Health Index currently stands at <strong>{current_val:.1f}</strong>, indicating a regime of <strong>{regime}</strong>. 
    Activity has shifted by <strong>{change_mom:+.1f}</strong> points month-over-month and <strong>{change_yoy:+.1f}</strong> points year-over-year.</p>
    
    <p><strong>Outlook:</strong> The 12-month forecast suggests conditions are {fc_trend}, projected to reach <strong>{fc_end_val:.1f}</strong>. 
    The primary support for the current environment is <strong>{top_driver}</strong>, while <strong>{lag_driver}</strong> remains a headwind.</p>
    
    <p><em>Recommendation:</em> Monitor {lag_driver} for signs of stabilization. Capitalize on favorable {top_driver} conditions.</p>
    """
    return summary
