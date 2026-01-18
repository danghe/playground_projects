
import pandas as pd
import numpy as np
from src.index.ma_index import build_index
from src.forecast.var_forecast import forecast_with_var
from app import apply_simulation_logic

def test_irf_calculation():
    print("--- 1. Building Index ---")
    df = build_index("config/signals.yaml")
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    print(f"Bucket Columns: {bucket_cols}")
    
    print("\n--- 2. Fitting VAR ---")
    var_input = df[bucket_cols].dropna()
    fc, var_results = forecast_with_var(var_input, steps=12)
    
    print("\n--- 3. Simulating Shocks (Rate=25, Conf=5, Vol=2) ---")
    shocks = apply_simulation_logic(25, 5, 2)
    print(f"Shocks Generated: {shocks}")
    
    print("\n--- 4. Calculating IRF ---")
    irf = var_results.irf(12)
    
    total_composite_response = pd.Series(0.0, index=range(13))
    
    # Mock weights mapping from app.py
    # app.py: weights_map = {f"BKT_{k}": v["weight"] for k, v in cfg["buckets"].items()}
    # But here we will just replicate the result based on columns
    # We need the config again to get weights
    # Or just assume equal weights/non-zero weights for verification
    # Actually let's just check if ANY response is generated
    
    for bucket_name, magnitude in shocks.items():
        if magnitude == 0: continue
        
        if bucket_name in var_input.columns:
            print(f"Processing Shock: {bucket_name} (Mag: {magnitude:.4f})")
            impulse_idx = list(var_input.columns).index(bucket_name)
            irf_values = irf.irfs[:, :, impulse_idx]
            
            # Just verify irf_values are not all zero
            max_irf = np.max(np.abs(irf_values))
            print(f"  -> Max IRF value for this shock: {max_irf:.6f}")
            
            if max_irf == 0:
                print("  !!! ALERT: IRF values are strictly ZERO. VAR model might be degenerate.")
        else:
            print(f"!!! Mismatch: {bucket_name} not in var_input.columns")

if __name__ == "__main__":
    test_irf_calculation()
