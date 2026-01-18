import pandas as pd
import yaml
from pathlib import Path
from typing import Dict
from src.data.fred_loader import load_series as load_fred_series
from src.data.sifma_loader import fetch_sifma_series
from src.data.renaissance_loader import fetch_ipo_counts
from src.data.imaa_loader import fetch_deal_counts
from src.data.sentiment_loader import fetch_sentiment_series
from src.data.valuation_loader import fetch_valuation_series
from src.features.normalize import normalize_series
from src.forecast.var_forecast import forecast_with_var
from src.plotting.plots import plot_composite, plot_buckets, plot_forecast, plot_dashboard
from src.reporting.narrative import generate_executive_summary
from src.reporting.report_generator import generate_html_report

def load_config(cfg_path: str) -> Dict:
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)

def sign_adjust(series: pd.Series, direction: str) -> pd.Series:
    return series if direction == "positive" else -series

def build_bucket(df_norm: pd.DataFrame) -> pd.Series:
    return df_norm.mean(axis=1)

def scale_0_100(x: pd.Series, window_months: int, neutral: float = 50.0) -> pd.Series:
    rmin = x.rolling(window_months, min_periods=60).min()
    rmax = x.rolling(window_months, min_periods=60).max()
    return 100 * (x - rmin) / (rmax - rmin)

def build_index(config_path: str = "config/signals.yaml") -> pd.DataFrame:
    cfg = load_config(config_path)
    start_date = cfg.get("start_date", "2010-01-01")

    bucket_values = {}
    for bucket_name, bucket in cfg["buckets"].items():
        frames = []
        for s in bucket["series"]:
            if s.get("source", "fred") == "fred":
                ser = load_fred_series(s["id"], agg=s["agg"], start="1990-01-01")
            elif s.get("source") == "sifma":
                ser = fetch_sifma_series("ig_issuance") if s["id"] == "SIFMA_IG_ISSUANCE" else fetch_sifma_series("hy_issuance")
            elif s.get("source") == "renaissance":
                ser = fetch_ipo_counts()
            elif s.get("source") == "imaa":
                ser = fetch_deal_counts()
            elif s.get("source") == "sentiment":
                ser = fetch_sentiment_series()
            elif s.get("source") == "valuation":
                ser = fetch_valuation_series()
            else:
                raise ValueError(f"Unknown source for series {s['name']}: {s.get('source')}")
            
            # Ensure all series are monthly end
            ser = ser.resample("ME").last()
            
            # Normalize first (on raw data)
            norm_cfg = cfg["normalize"]
            ser_n = normalize_series(ser, norm_cfg["method"], norm_cfg["window"], norm_cfg["clip_z"])
            
            # Invert Z-scores for negative indicators (Higher is Better rule)
            if s["direction"] == "negative":
                ser_n = ser_n * -1
            
            ser_n.name = s["name"]
            frames.append(ser_n)
            print(f"Loaded {s['name']}: Start {ser.index.min()}, End {ser.index.max()}")

            # Keep raw CI_LOANS for plotting
            if s["name"] == "CI_LOANS":
                bucket_values["CI_LOANS_RAW"] = ser
            
            # Keep raw BUSINESS_CONFIDENCE for plotting
            if s["name"] == "BUSINESS_CONFIDENCE":
                bucket_values["BUSINESS_CONFIDENCE_RAW"] = ser

        if frames:
            bucket_df = pd.concat(frames, axis=1).dropna(how="all")
            bucket_values[bucket_name] = build_bucket(bucket_df)
    if not bucket_values:
        raise RuntimeError("No bucket values built")
    
    # Separate raw series from buckets
    raw_series_keys = ["CI_LOANS_RAW", "BUSINESS_CONFIDENCE_RAW"]
    raw_series = {k: v for k, v in bucket_values.items() if k in raw_series_keys}
    bucket_values = {k: v for k, v in bucket_values.items() if k not in raw_series_keys}
    
    buckets_df = pd.DataFrame(bucket_values).dropna().copy()
    
    # Apply weights to create composite
    weighted_buckets = buckets_df.copy()
    for b in weighted_buckets.columns:
        weighted_buckets[b] = weighted_buckets[b] * cfg["buckets"][b]["weight"]
    
    composite = weighted_buckets.sum(axis=1)
    composite_0_100 = scale_0_100(composite, window_months=cfg["scale"]["window_months"], neutral=cfg["scale"]["neutral"])
    
    out = pd.DataFrame({"CompositeRaw": composite, "Composite": composite_0_100}, index=composite.index)
    # Join with the weighted bucket values for contribution analysis
    out = out.join(weighted_buckets.add_prefix("BKT_"))
    
    # Join raw series
    if raw_series:
        out = out.join(pd.DataFrame(raw_series))
        
    return out

if __name__ == "__main__":
    print("Building Index...")
    df = build_index("config/signals.yaml")
    
    # Ensure output directory exists
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True, parents=True)
    
    # Save Data
    df.to_csv(out_dir / "ma_health_index.csv")
    print(f"Index built: {len(df)} months")
    
    # Forecast (VAR)
    print("Running VAR Forecast...")
    # Prepare data for VAR: Use the weighted bucket columns
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    var_input = df[bucket_cols].dropna()
    
    fc_df, var_results = forecast_with_var(var_input, steps=12)
    
    # Scale the forecasted composite to 0-100 using the same parameters (approximate)
    # Note: Ideally we'd use the scaler fitted on history, but for now we'll project the change
    # or just re-scale the concatenated series.
    
    # Better approach: Append forecast to history and re-scale
    # But `scale_0_100` uses rolling windows, so we can just append and scale.
    
    # For simplicity in this prototype, let's map the forecasted Composite_Index (which is sum of weighted Z-scores)
    # to the 0-100 scale using the recent relationship or just re-run the scaler on the extended series.
    
    # Let's extend the raw composite and re-scale
    history_raw = df["CompositeRaw"]
    forecast_raw = fc_df["Composite_Index"]
    combined_raw = pd.concat([history_raw, forecast_raw])
    
    cfg = load_config("config/signals.yaml")
    combined_scaled = scale_0_100(combined_raw, window_months=cfg["scale"]["window_months"], neutral=cfg["scale"]["neutral"])
    
    # Extract the forecast part
    fc_scaled = combined_scaled.iloc[-12:]
    fc_df["forecast"] = fc_scaled
    
    # Add confidence intervals (simplified for VAR - just using a fixed width for now or from VAR results if we want to be fancy)
    # VAR results give us standard errors, but mapping that through the 0-100 scale is non-trivial.
    # We'll use a simple heuristic for the prototype: +/- 5 points growing over time
    fc_df["lower80"] = fc_df["forecast"] - [i*0.5 + 2 for i in range(1, 13)]
    fc_df["upper80"] = fc_df["forecast"] + [i*0.5 + 2 for i in range(1, 13)]
    
    fc_df.to_csv(out_dir / "forecast.csv")
    
    # Generate Plots
    print("Generating Visuals...")
    plot_composite(df, str(out_dir / "index_history.png"))
    plot_buckets(df, str(out_dir / "drivers.png"))
    plot_forecast(df["Composite"], fc_df, str(out_dir / "forecast.png"))
    plot_dashboard(df, fc_df, str(out_dir / "dashboard.png"))
    
    # Generate Narrative
    print("Generating Narrative...")
    summary = generate_executive_summary(df, fc_df)
    
    # Generate Report
    print("Compiling Report...")
    plots = {
        "Executive Dashboard": str(out_dir / "dashboard.png"),
        "Historical Trend": str(out_dir / "index_history.png"),
        "Market Drivers": str(out_dir / "drivers.png"),
        "12-Month Forecast": str(out_dir / "forecast.png")
    }
    generate_html_report(summary, plots, str(out_dir / "report.html"))
    
    print("Done! Report saved to output/report.html")
