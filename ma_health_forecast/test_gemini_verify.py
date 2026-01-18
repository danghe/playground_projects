import pandas as pd
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.index.ma_index import build_index, load_config
from app import SCENARIO_MAPPING, calculate_scenario_forecast
from src.forecast.var_forecast import forecast_with_var

def test_normalization():
    print("Testing Normalization...")
    df = build_index("config/signals.yaml")
    print(f"Index built. Shape: {df.shape}")
    return df

def test_scenario(df):
    print("Testing Scenario Logic...")
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    var_input = df[bucket_cols].dropna()
    fc, var_results = forecast_with_var(var_input, steps=12)
    
    scenario_name = "Fed Pivot: Aggressive Rate Cuts & Credit Easing"
    print(f"Simulating: {scenario_name}")
    
    scenario_fc = calculate_scenario_forecast(var_results, fc, scenario_name, bucket_cols)
    
    baseline = fc["Composite_Index"]
    diff = scenario_fc - baseline
    
    print(f"Mean Difference: {diff.mean()}")
    
    if diff.mean() > 0:
        print("PASS: Optimistic scenario increased the index.")
    else:
        print("FAIL: Optimistic scenario did not increase the index.")
        print("Difference values:", diff.values)

if __name__ == "__main__":
    try:
        df = test_normalization()
        test_scenario(df)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
