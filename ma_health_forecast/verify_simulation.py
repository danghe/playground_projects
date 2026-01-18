
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from app import generate_dashboard_data

def verify_logic():
    print("Running simulation (Rate=100bps, Neutral, Normal)...")
    
    # 1. Baseline (0 shocks)
    try:
        baseline_data = generate_dashboard_data(0, 0, 0)
    except Exception as e:
        print(f"Error generating baseline: {e}")
        return

    if not baseline_data.get('plots'):
        print("No plot data returned. Data fetch likely failed.")
        return

    # We need to extract the raw values. 
    # generate_dashboard_data returns base64 plots. It doesn't return the raw dataframe in the dictionary.
    # We might need to modify app.py temporarily or inspect the cache, 
    # or rely on the logic inside generate_dashboard_data.
    
    # Actually, to verify the math, we should import the helper functions and run them,
    # recreating the logic from generate_dashboard_data but accessing the intermediates.
    
    from app import get_cached_data, scale_0_100, apply_simulation_logic, calculate_scenario_forecast, load_config
    
    df, fc_df, var_results = get_cached_data()
    if df.empty:
        print("Cache empty.")
        return
        
    # Replicate scaling logic from generate_dashboard_data
    forecast_raw = fc_df["Composite_Index"] if "Composite_Index" in fc_df else fc_df.sum(axis=1)
    history_raw = df["CompositeRaw"]
    combined_raw = pd.concat([history_raw, forecast_raw])
    cfg = load_config("config/signals.yaml")
    combined_scaled = scale_0_100(combined_raw, window_months=cfg["scale"]["window_months"], neutral=cfg["scale"]["neutral"])
    
    baseline_forecast_series = combined_scaled.iloc[-12:]
    print(f"Baseline Forecast (Tail):\n{baseline_forecast_series.tail()}")

    # Apply Shocks
    # Rate: 100bps
    shocks = apply_simulation_logic(100, 'Neutral', 'Normal')
    print(f"\nShocks calculated: {shocks}")
    
    weights_map = {f"BKT_{k}": v["weight"] for k, v in cfg["buckets"].items()}
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    
    scenario_series = calculate_scenario_forecast(var_results, baseline_forecast_df=baseline_forecast_series, shocks=shocks, bucket_order=bucket_cols, weights=weights_map)
    
    print("\nScenario Forecast (Tail):")
    print(scenario_series.tail())
    
    diff = scenario_series - baseline_forecast_series
    print(f"\nDifferences (Impact):\n{diff.tail()}")
    print(f"\nMean Impact: {diff.mean()}")
    
    if abs(diff.mean()) < 2.0:
        print("FAIL: Impact is too small to be visible (likely < 2 points).")
    else:
        print("PASS: Impact is significant.")

if __name__ == "__main__":
    verify_logic()
