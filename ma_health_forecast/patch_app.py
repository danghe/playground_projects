import os

# New Function content: Robust Parsing + 5x Sensitivity + Capitalized Keys
NEW_FUNC = """def apply_simulation_logic(rate_change, confidence_shock, volatility_shock):
    \"\"\"
    Maps user inputs to specific bucket shocks.
    TUNED for visual responsiveness (approx 5x sensitivity).
    FIXED: Handles numeric strings properly.
    \"\"\"
    shocks = {}
    
    # 1. Rate Impact
    r_chg = 0.0
    try:
        r_chg = float(rate_change)
    except: 
        r_chg = 0.0
    
    # Rate: 100bps -> 2.5 SD shock
    rate_impact = -1 * (r_chg / 100.0) * 2.5
    
    # 2. Confidence Impact
    c_val = 0.0
    # Try float first (e.g. "-5")
    try:
        c_val = float(confidence_shock)
    except:
        # Fallback to string keywords
        if isinstance(confidence_shock, str):
            if 'Bear' in confidence_shock: c_val = -20.0
            elif 'Bull' in confidence_shock: c_val = 20.0
            else: c_val = 0.0
        else:
            c_val = 0.0
    
    # Confidence: 20 pts -> 5.0 SD shock
    conf_impact = (c_val / 20.0) * 5.0

    # 3. Volatility Impact
    v_val = 0.0
    try:
        v_val = float(volatility_shock)
    except:
        if isinstance(volatility_shock, str):
            if 'High' in volatility_shock: v_val = 10.0
            elif 'Low' in volatility_shock: v_val = -5.0
            else: v_val = 0.0
        else:
            v_val = 0.0
        
    # Volatility: 10 pts -> 4.0 SD shock
    vol_impact = -1 * (v_val / 10.0) * 4.0
    
    # Apply to buckets (Use Capitalized Keys to match VAR columns)
    shocks["BKT_Credit"] = rate_impact + (vol_impact * 0.5)
    shocks["BKT_Sentiment"] = conf_impact + (vol_impact * 0.2) 
    shocks["BKT_Valuation"] = rate_impact 
    shocks["BKT_Volatility"] = vol_impact 
    shocks["BKT_Liquidity"] = rate_impact + (conf_impact * 0.3) 
    
    return shocks
"""

file_path = "d:/00Intralinks/M&A Forecast Project/ma_health_forecast_project/ma_health_forecast/app.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Markers to locate the function block
start_marker = "def apply_simulation_logic(rate_change, confidence_shock, volatility_shock):"
next_func_marker = "def calculate_scenario_forecast"

start_idx = content.find(start_marker)
if start_idx == -1:
    print("Error: Could not find function start")
    exit(1)

next_func_idx = content.find(next_func_marker, start_idx)
if next_func_idx == -1:
    print("Error: Could not find next function")
    exit(1)

# Replace the block
content_new = content[:start_idx] + NEW_FUNC + "\n" + content[next_func_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content_new)

print("Successfully patched app.py with robust parsing logic.")
