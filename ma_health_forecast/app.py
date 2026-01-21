from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, stream_with_context
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import os
import sqlite3
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables before any src imports
load_dotenv()

# --- Core Modules ---
from src.index.ma_index import build_index, load_config, scale_0_100
from src.forecast.var_forecast import forecast_with_var
from src.forecast.llm_forecast import gemini_forecast
from src.reporting.narrative import generate_executive_summary, get_regime

# --- Analysis Modules ---
from src.analysis.strategic_radar import scan_sector_audit_streaming, scan_sector_audit, get_radar_cache
from src.analysis.gemini_brief import brief_service
from src.analysis.gemini_dossier import dossier_service
from src.data.retrieval_service import retrieval_service
from src.data.schema import get_db_path
from src.analysis.profile_engine import build_user_profile
from src.analysis.matchmaker import MatchEngine
from src.analysis.gemini_architect import GeminiArchitect
from src.analysis.deal_architect_deep_dive import perform_live_dossier

app = Flask(__name__)
print("--- STARTING APP: v2.2 (Help Page + Deal Command Fixes) ---")

# --- HELPERS ---

def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def plot_to_base64(fig):
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    b64 = base64.b64encode(img.getvalue()).decode()
    plt.close(fig)
    return b64

# --- MACRO INDEX CACHE ---
CACHED_INDEX = None
CACHED_FORECAST = None
CACHED_VAR_RESULTS = None

def get_cached_data():
    global CACHED_INDEX, CACHED_FORECAST, CACHED_VAR_RESULTS
    if CACHED_INDEX is None:
        print("Fetching data and building index (First Run)...")
        try:
            CACHED_INDEX = build_index("config/signals.yaml")
            print("Fitting VAR model...")
            bucket_cols = [c for c in CACHED_INDEX.columns if c.startswith("BKT_")]
            var_input = CACHED_INDEX[bucket_cols].dropna()
            CACHED_FORECAST, var_res = forecast_with_var(var_input, steps=12)
            CACHED_VAR_RESULTS = var_res
        except Exception as e:
            print(f"Error building index: {e}")
            return pd.DataFrame(), None, None
    return CACHED_INDEX, CACHED_FORECAST, CACHED_VAR_RESULTS

# --- PLOT GENERATORS (In-memory Base64) ---

def generate_main_forecast_plot(df, fc_df, ai_fc=None):
    """Main forecast chart with history + VAR + optional AI overlay."""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    last_hist_date = df.index[-1]
    last_hist_val = df["Composite"].iloc[-1]
    
    # 1. Prepare continuous lines (connect history to forecast)
    baseline_plot = pd.concat([pd.Series([last_hist_val], index=[last_hist_date]), fc_df["forecast"]])
    # Scenario Plot (New)
    scenario_plot = None
    if "scenario_forecast" in fc_df and fc_df["scenario_forecast"] is not None:
        scenario_plot = pd.concat([pd.Series([last_hist_val], index=[last_hist_date]), fc_df["scenario_forecast"]])

    lower80_plot = pd.concat([pd.Series([last_hist_val], index=[last_hist_date]), fc_df["lower80"]])
    upper80_plot = pd.concat([pd.Series([last_hist_val], index=[last_hist_date]), fc_df["upper80"]])
    
    # Plot History
    # Colors: Intralinks Blue (#005587)
    hist_subset = df["Composite"].iloc[-60:]
    ax.plot(hist_subset.index, hist_subset.values, label="History", color="#005587", linewidth=2)
    
    # Plot Baseline VAR
    # Colors: Intralinks Gold (#FFB81C)
    ax.plot(baseline_plot.index, baseline_plot.values, label="Baseline Forecast (VAR)", color="#FFB81C", linestyle="--", linewidth=2)
    
    # Plot Simulated Scenario (Red)
    if scenario_plot is not None:
         ax.plot(scenario_plot.index, scenario_plot.values, label="Simulated Scenario", color="#d62728", linestyle="-.", linewidth=2)

    # Confidence Intervals
    ax.fill_between(lower80_plot.index, lower80_plot.values, upper80_plot.values, color="#FFB81C", alpha=0.2)

    # AI Overlay (if provided)
    if ai_fc is not None and not ai_fc.empty:
        ai_plot = pd.concat([pd.Series([last_hist_val], index=[last_hist_date]), ai_fc])
        ax.plot(ai_plot.index, ai_plot.values, label="AI Forecast (Gemini)", color="#9467bd", linestyle=":", linewidth=2.5, marker='o', markersize=4)
    
    # Neutral Line
    ax.axhline(50, color='gray', linestyle=':', alpha=0.5)
    
    chart_title = "M&A Health Index (VAR + AI Forecast)" if (ai_fc is not None and not ai_fc.empty) else "M&A Health Index (VAR Forecast)"
    ax.set_title(chart_title, fontweight='bold')
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.2)
    ax.set_ylim(0, 100)
    
    return plot_to_base64(fig)

def generate_attribution_plot(df):
    """Horizontal bar chart of current drivers."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    latest = df[bucket_cols].iloc[-1]
    latest.index = [c.replace("BKT_", "").replace("_", " ").title() for c in latest.index]
    
    color_map = {
        "Credit": "#1f77b4", 
        "Sentiment": "#ff7f0e", 
        "Valuation": "#2ca02c", 
        "Volatility": "#d62728", 
        "Liquidity": "#9467bd"
    }
    colors = [color_map.get(x, "#333333") for x in latest.index]
    
    latest.plot(kind='barh', ax=ax, color=colors, alpha=0.8)
    ax.set_title("Current Drivers (Weighted Contribution)", fontweight='bold')
    ax.axvline(0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.2)
    
    return plot_to_base64(fig)

def generate_irf_plot(var_results, var_input, shocks, weights_map):
    """Impulse Response Function plot."""
    fig, ax = plt.subplots(figsize=(10, 6))
    try:
        if var_results is None:
            raise ValueError("No VAR model results available")
            
        irf = var_results.irf(12)
        total_composite_response = pd.Series(0.0, index=range(13))
        
        for bucket_name, magnitude in shocks.items():
            if magnitude == 0: continue
            if bucket_name in var_input.columns:
                impulse_idx = list(var_input.columns).index(bucket_name)
                # orth_irfs is (steps, vars, shocks)
                irf_values = irf.orth_irfs[:, :, impulse_idx]
                
                # Weighted sum of response across all variables
                for i, col in enumerate(var_input.columns):
                    w = weights_map.get(col, 0)
                    resp = irf_values[:, i] * magnitude
                    total_composite_response += resp * w
                    
        ax.plot(total_composite_response, marker='o', color='#d62728', linewidth=2, label="Net Impact on Index")
        ax.axhline(0, color='black', linewidth=0.5)
        ax.set_title("Net Impulse Response (Combined Shocks)", fontweight='bold')
        ax.grid(True, alpha=0.2)
        ax.legend()
    except Exception as e:
        ax.text(0.5, 0.5, f"No Impact / Static: {str(e)}", ha='center')
        
    return plot_to_base64(fig)

def generate_history_plot(df):
    """Long-term history with regime shading."""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Regime Shading
    ax.axhspan(50, 100, color='green', alpha=0.05, label='Expansionary')
    ax.axhspan(0, 50, color='red', alpha=0.05, label='Contractionary')
    
    # Plot Index and Trend
    df["Composite"].plot(ax=ax, label="M&A Health Index", color="#005587", linewidth=2)
    df["Composite"].rolling(12).mean().plot(ax=ax, label="12-Month Trend", color="#FFB81C", linewidth=2, linestyle="--")
    
    ax.set_title("M&A Historical Health Index Performance", fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left")
    
    return plot_to_base64(fig)

def generate_contributions_plot(df):
    """Time series of component contributions."""
    fig, ax = plt.subplots(figsize=(10, 5))
    cols = [c for c in df.columns if c.startswith("BKT_")]
    plot_df = df[cols].copy()
    plot_df.columns = [c.replace("BKT_", "").replace("_", " ").title() for c in cols]
    
    color_map = {
        "Credit": "#1f77b4", 
        "Sentiment": "#ff7f0e", 
        "Valuation": "#2ca02c", 
        "Volatility": "#d62728", 
        "Liquidity": "#9467bd"
    }
    plot_colors = [color_map.get(label, "#333333") for label in plot_df.columns]
    
    plot_df.iloc[-60:].plot(ax=ax, linewidth=1.5, alpha=0.8, color=plot_colors)
    ax.set_title("Component Contributions (Time Series)", fontweight='bold')
    ax.grid(True, alpha=0.2)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
    plt.tight_layout()
    
    return plot_to_base64(fig)

def generate_deal_activity_plot(df):
    """Deal activity proxy (C&I Loans)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    deal_proxy_col = None
    if "CI_LOANS_RAW" in df.columns: deal_proxy_col = "CI_LOANS_RAW"
    else:
        for col in df.columns:
            if "CI_LOANS" in col or "BUSLOANS" in col: 
                 deal_proxy_col = col
                 break
                 
    if deal_proxy_col:
        deal_activity = df[deal_proxy_col].pct_change(12) * 100
        deal_activity.iloc[-120:].plot(ax=ax, color="#2ca02c", linewidth=2, label="C&I Loans (YoY Growth)")
        ax.axhline(0, color='black', linewidth=0.5)
        ax.set_title("Deal Activity Proxy: Commercial & Industrial Loans Growth", fontweight='bold')
        ax.legend(loc="upper left")
        
    ax.grid(True, alpha=0.2)
    return plot_to_base64(fig)

def generate_confidence_plot(df):
    """CEO Confidence plot."""
    fig, ax = plt.subplots(figsize=(10, 5))
    conf_col = "BUSINESS_CONFIDENCE_RAW"
    if conf_col in df.columns:
        df[conf_col].iloc[-120:].plot(ax=ax, color="#ff7f0e", linewidth=2, label="CEO Confidence (OECD BCI)")
        ax.axhline(100, color='black', linewidth=0.5, linestyle="--", label="Neutral (100)")
        ax.set_title("CEO Confidence: OECD Business Confidence Indicator (USA)", fontweight='bold')
        ax.legend(loc="upper left")
        
    ax.grid(True, alpha=0.2)
    return plot_to_base64(fig)

def apply_simulation_logic(rate_change, confidence_shock, volatility_shock):
    """
    Maps user inputs to specific bucket shocks.
    TUNED for visual responsiveness (approx 5x sensitivity).
    FIXED: Handles numeric strings properly.
    """
    shocks = {}
    
    # 1. Rate Impact
    r_chg = 0.0
    try:
        r_chg = float(rate_change)
    except: 
        r_chg = 0.0
    
    # Rate: 100bps -> 15.0 Index Points shock (Tuned for 0-100 scale)
    rate_impact = -1 * (r_chg / 100.0) * 15.0
    
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
    
    # Confidence: 20 pts -> 20.0 Index Points shock
    conf_impact = (c_val / 20.0) * 20.0

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
        
    # Volatility: 10 pts -> 15.0 Index Points shock
    vol_impact = -1 * (v_val / 10.0) * 15.0
    
    # Apply to buckets (Use Capitalized Keys to match VAR columns)
    shocks["BKT_Credit"] = rate_impact + (vol_impact * 0.5)
    shocks["BKT_Sentiment"] = conf_impact + (vol_impact * 0.2) 
    shocks["BKT_Valuation"] = rate_impact 
    shocks["BKT_Volatility"] = vol_impact 
    shocks["BKT_Liquidity"] = rate_impact + (conf_impact * 0.3) 
    
    return shocks

def calculate_scenario_forecast(var_results, baseline_forecast_df, shocks, bucket_order, weights):
    """
    Calculates the new forecast trajectory based on a multi-variable shock vector.
    """
    forecast_horizon = 12
    irf = var_results.irf(periods=forecast_horizon)
    orth_irfs = irf.orth_irfs 
    
    total_impact = np.zeros(forecast_horizon + 1)

    for bucket_name, magnitude in shocks.items():
        if magnitude == 0:
            continue
            
        try:
            # Handle naming mismatch (BKT_ prefix and Case)
            # bucket_order usually has 'BKT_credit' etc.
            
            # Normalize list and key
            bucket_order_norm = [b.lower() for b in bucket_order]
            key_norm = bucket_name.lower()
            
            if key_norm in bucket_order_norm:
                 shock_index = bucket_order_norm.index(key_norm)
            elif key_norm.replace("bkt_", "") in bucket_order_norm:
                 shock_index = bucket_order_norm.index(key_norm.replace("bkt_", ""))
            else:
                 continue

            response_matrix = orth_irfs[:, :, shock_index]
            scaled_impact_matrix = response_matrix * magnitude
            
            weighted_impact = np.zeros(forecast_horizon + 1)
            for i, col_name in enumerate(bucket_order):
                # Weights map usually keys are 'BKT_credit'
                w = 0.0
                if col_name in weights: w = weights[col_name]
                elif f"BKT_{col_name}" in weights: w = weights[f"BKT_{col_name}"]
                
                weighted_impact += scaled_impact_matrix[:, i] * w
            
            total_impact += weighted_impact
            
        except ValueError:
            continue

    cumulative_impact = np.cumsum(total_impact)
    
    if len(cumulative_impact) > forecast_horizon:
        aligned_impact = cumulative_impact[1:forecast_horizon+1]
    else:
        aligned_impact = cumulative_impact[:forecast_horizon]

    # Baseline forecast is 0-100. We add the impact.
    scenario_values = baseline_forecast_df.values + aligned_impact
    
    return pd.Series(scenario_values, index=baseline_forecast_df.index, name="Scenario_Forecast")

# --- FULL DASHBOARD DATA GENERATOR ---



def generate_dashboard_data(rate_change=0, confidence_shock='Neutral', volatility_shock='Normal', include_ai_forecast=False):
    df, fc_df, var_results = get_cached_data()
    if df.empty:
        return {"latest_val": 0, "fc_val": 0, "plots": {}, "descriptions": {}}

    # Forecast (VAR) - Restore Backup Logic
    # 1. Reconstruct Forecast Composite from FC DF
    # backup uses forecast_with_var then scales.
    # forecast_with_var returns df with 'Composite_Index' (sum of components).
    # We need to scale it using history.
    
    forecast_raw = fc_df["Composite_Index"] if "Composite_Index" in fc_df else fc_df.sum(axis=1)
    history_raw = df["CompositeRaw"]
    
    combined_raw = pd.concat([history_raw, forecast_raw])
    
    cfg = load_config("config/signals.yaml")
    
    # Use imported scale_0_100 or define local? Imported is available.
    combined_scaled = scale_0_100(combined_raw, window_months=cfg["scale"]["window_months"], neutral=cfg["scale"]["neutral"])
    
    # Create fc dict
    fc = {}
    fc["forecast"] = combined_scaled.iloc[-12:]
    
    # Confidence Intervals (Simple logic from backup)
    fc["lower80"] = fc["forecast"] - [i*0.5 + 2 for i in range(1, 13)]
    fc["upper80"] = fc["forecast"] + [i*0.5 + 2 for i in range(1, 13)]
    
    # Scenario Forecast using Helper
    shocks = apply_simulation_logic(rate_change, confidence_shock, volatility_shock)
    bucket_cols = [c for c in df.columns if c.startswith("BKT_")]
    weights_map = {f"BKT_{k}": v["weight"] for k, v in cfg["buckets"].items()} # ensure keys match columns
    
    # calculate_scenario_forecast expects bucket columns in var_results to match order
    # Helper handles mismatch if names are close.
    # var_results bucket order usually matches input df columns.
    
    scenario_series = calculate_scenario_forecast(var_results, fc["forecast"], shocks, bucket_cols, weights_map)
    fc["scenario_forecast"] = scenario_series
    
    # AI Forecast
    fc["ai_forecast"] = None
    if include_ai_forecast:
        try:
             # Ensure robust type conversion
             r_val = float(rate_change) if rate_change else 0
             c_val = 0
             if isinstance(confidence_shock, str):
                 if confidence_shock == 'Bear': c_val = -20
                 elif confidence_shock == 'Bull': c_val = 20
             else: c_val = float(confidence_shock) if confidence_shock else 0
             
             v_val = 0
             if isinstance(volatility_shock, str):
                 if volatility_shock == 'High': v_val = 10
             else: v_val = float(volatility_shock) if volatility_shock else 0

             gemini_fc, _ = gemini_forecast(
                df["Composite"], 
                steps=12, 
                rate_shock=int(r_val),
                confidence_shock=int(c_val), 
                volatility_shock=int(v_val)
             )
             if gemini_fc is not None and not gemini_fc.empty:
                 fc["ai_forecast"] = gemini_fc["forecast"]
        except Exception as e:
            print(f"AI Forecast Error: {e}")

    latest_val = df["Composite"].iloc[-1]
    fc_val = fc["forecast"].iloc[-1]
    
    # Generate Executive Summary (Restoring missing piece)
    regime = get_regime(latest_val)
    # Default placeholder matching "Good State"
    executive_summary = f"<h5>Market Overview</h5><p>The M&A Health Index currently stands at <strong>{latest_val:.1f}</strong>.</p><p class='text-muted small'>Enable 'Include AI Forecast' for AI-powered insights and predictions.</p>"
    
    # Try to generate a basic summary even without AI enabled if possible?
    # Or just ensure it's not the error string.
    # The error string in UI is caused by JS when fetch fails or data missing.
    # If we return a string here, UI should display it.
    
    if include_ai_forecast and fc["ai_forecast"] is not None:
         # Note: This is mainly for initial load if AI was somehow enabled by default, 
         # but usually frontend fetches narrative separately.
         # This block ensures 'executive_summary' in the JSON response is structured correctly if used.
         try:
             # Basic placeholder if we have AI forecast but haven't fetched narrative text here
             # (Since we moved detailed narrative gen to /api/narrative usually)
             executive_summary = f"<h5>Market Overview</h5><p>The M&A Health Index currently stands at <strong>{latest_val:.1f}</strong>.</p><p class='text-success small'>AI Analysis Generated.</p>"
         except Exception:
             executive_summary = f"<h5>Market Overview</h5><p>The M&A Health Index currently stands at <strong>{latest_val:.1f}</strong>.</p>"
    else:
        # Static Summary
        executive_summary = f"<h5>Market Overview</h5><p>The M&A Health Index currently stands at <strong>{latest_val:.1f}</strong>.</p><p class='text-muted small'>Enable 'Include AI Forecast' for AI-powered insights and predictions.</p>"

    # Generate all plots
    plots = {
        "plot_url": generate_main_forecast_plot(df, fc, fc["ai_forecast"]),
        "attribution_url": generate_attribution_plot(df),
        "irf_url": generate_irf_plot(var_results, df[[c for c in df.columns if c.startswith("BKT_")]], shocks, weights_map),
        "history_url": generate_history_plot(df),
        "contributions_url": generate_contributions_plot(df),
        "deal_activity_url": generate_deal_activity_plot(df),
        "confidence_url": generate_confidence_plot(df),
    }
    
    # Graph Descriptions
    descriptions = {
        "plot_url": "Shows the historical and forecasted M&A Health Index. The baseline forecast uses a Vector Autoregression (VAR) model. The simulated scenario adjusts the forecast based on user-defined shocks. The AI forecast (if enabled) provides an alternative perspective using Gemini.",
        "irf_url": "Illustrates the estimated impact of the selected shocks (Interest Rate, Confidence, Volatility) on the M&A Health Index over the next 12 months, based on the VAR model's relationships.",
        "attribution_url": "Breaks down the current M&A Health Index into its constituent drivers, showing the weighted contribution of each component (Credit, Sentiment, Valuation, Volatility, Liquidity).",
        "history_url": "Displays the long-term historical performance of the M&A Health Index, including a 12-month moving average to highlight trends. Green and red zones indicate expansionary (>50) and contractionary (<50) periods.",
        "contributions_url": "Shows how the contribution of each component (Credit, Sentiment, Valuation, Volatility, Liquidity) to the overall index has evolved over time.",
        "deal_activity_url": "A proxy for M&A deal activity, represented by the year-over-year growth rate of Commercial & Industrial Loans (Source: FRED).",
        "confidence_url": "Tracks CEO confidence using the OECD Business Confidence Indicator for the USA. Values above 100 indicate optimism, while values below 100 indicate pessimism (Source: FRED)."
    }
    
    return {
        "latest_val": round(latest_val, 1),
        "fc_val": round(fc_val, 1),
        "plots": plots,
        "descriptions": descriptions,
        "executive_summary": executive_summary
    }

# --- ROUTES: MACRO FORECAST ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return redirect(url_for('index'))
    
    data = generate_dashboard_data(0, 'Neutral', 'Normal')
    
    # Flatten for template - it expects plot_url, attribution_url etc at top level
    template_data = {
        'latest_val': data['latest_val'],
        'fc_val': data['fc_val'],
        'descriptions': data['descriptions'],
        **data['plots']  # Flatten plots dict
    }
    return render_template('index.html', **template_data)

@app.route('/api/update_forecast', methods=['POST'])
def update_forecast():
    req = request.json
    data = generate_dashboard_data(
        req.get('rate_change', 0),
        req.get('confidence_shock', 0),
        req.get('volatility_shock', 0),
        req.get('include_ai', False)
    )
    return jsonify(data)

@app.route('/api/narrative', methods=['POST'])
def narrative():
    """Generate executive summary narrative."""
    req = request.json
    include_ai = req.get('include_ai', False)
    
    # Defaults
    rate_change = req.get('rate_change', 0)
    conf_shock = req.get('confidence_shock', 0)
    vol_shock = req.get('volatility_shock', 0)
    
    # FIX: unpack 3 values (df, fc, var_results) - ignore var_results
    df, fc_df, _ = get_cached_data()
    if df.empty:
        return jsonify({"html": "<p>Data unavailable.</p>"})
    
    latest_val = df["Composite"].iloc[-1]
    
    # 1. Base Summary (Market Overview)
    summary_html = f"<h5>Market Overview</h5><p>The M&A Health Index currently stands at <strong>{latest_val:.1f}</strong>.</p>"
    
    # 2. If AI requested, try to get LLM rationale
    if include_ai:
        try:
            # We need to run the forecast to get the rationale context
            # Make sure we pass the correct types!
            r_val = float(rate_change) if rate_change else 0
            
            # Helper for casting
            def safe_shock(val, map_str):
                if isinstance(val, str) and val in map_str: return map_str[val]
                try: return float(val)
                except: return 0
                
            c_val = safe_shock(conf_shock, {'Bear': -20, 'Bull': 20, 'Neutral': 0})
            v_val = safe_shock(vol_shock, {'High': 10, 'Normal': 0, 'Low': -10})

            _, rationale = gemini_forecast(
                df["Composite"], 
                steps=12,
                rate_shock=int(r_val),
                confidence_shock=int(c_val),
                volatility_shock=int(v_val)
            )
            
            if rationale and "Forecast failed" not in rationale:
                summary_html += f"<hr><h4>AI Strategic Insight</h4>{rationale}"
            else:
                 summary_html += f"<p class='text-muted small mt-2'>AI analysis unavailable (Service Busy).</p>"
                 
        except Exception as e:
            # Ensure we still return the base summary, just append error note
            print(f"Narrative Error: {e}")
            summary_html += f"<p class='text-muted small mt-2'>AI analysis temporarily unavailable.</p>"
    else:
        summary_html += "<p class='text-muted small'>Enable 'Include AI Forecast' for AI-powered insights and predictions.</p>"
    
    return jsonify({"html": summary_html})

# --- ROUTES: DEAL RADAR (STRATEGIC) ---

@app.route('/deal-radar')
def deal_radar():
    sector = request.args.get('sector', 'Tech')
    sectors = ['Tech', 'Healthcare', 'Financials', 'Consumer', 'Energy', 'Industrials', 'Real Estate']
    
    # Check cache first for fast load
    cached = get_radar_cache(sector)
    if cached:
        targets, heatmap, narrative, playbook = cached
        
        # Build market_state from data
        import yfinance as yf
        vix_val = 20.0
        try:
            hist = yf.Ticker("^VIX").history(period="5d")
            if not hist.empty:
                vix_val = hist['Close'].iloc[-1]
        except:
            pass
        
        market_state = {
            'deal_window_score': 75 if vix_val < 20 else (50 if vix_val < 30 else 25),
            'financing': 'Open' if vix_val < 25 else 'Restricted',
            'vol_value': round(vix_val, 1),
            'volatility': 'Low' if vix_val < 15 else ('Moderate' if vix_val < 25 else 'High'),
            'seller_pressure': 'Moderate',
            'pipeline': f'{len(targets)} companies'
        }
        
        return render_template('deal_radar.html',
                               sector=sector,
                               sectors=sectors,
                               market_state=market_state,
                               targets=targets,
                               heatmap=heatmap,
                               narrative=narrative,
                               playbook=playbook)
    
    # No cache - render skeleton (SSE will populate)
    market_state = {
        'deal_window_score': '--',
        'financing': '...',
        'vol_value': '--',
        'volatility': '...',
        'seller_pressure': '...',
        'pipeline': '...'
    }
    
    return render_template('deal_radar.html',
                           sector=sector,
                           sectors=sectors,
                           market_state=market_state,
                           targets=[],
                           heatmap=[],
                           narrative=[],
                           playbook=None)

@app.route('/api/deal-radar/stream')
def deal_radar_stream():
    """SSE Endpoint for Real-time Loading Bar."""
    sector = request.args.get('sector', 'Tech')
    
    def generate():
        scanner = scan_sector_audit_streaming(sector)
        for update in scanner:
            data_str = json.dumps(update)
            yield f"data: {data_str}\n\n"
            if update.get('complete'):
                break
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/deal-radar/data')
def deal_radar_data():
    """Fallback / Debug Data endpoint"""
    sector = request.args.get('sector', 'Tech')
    res = scan_sector_audit(sector)
    if res:
        targets, heatmap, narrative, playbook = res
        return jsonify({"targets": targets, "heatmap": heatmap, "narrative": narrative, "playbook": playbook})
    return jsonify({"error": "Scan failed"})

# --- LEGACY BRIEF ENDPOINT (For Radar UI) ---
@app.route('/api/industry-brief', methods=['POST'])
def industry_brief():
    data = request.json
    sector = data.get('sector')
    sub_industry = data.get('sub_industry', 'All')
    force = data.get('force_refresh', False)
    
    conn = get_db()
    cursor = conn.cursor()
    
    db_sector = 'Technology' if sector == 'Tech' else sector
    cursor.execute("SELECT AVG(s.spi) FROM scores s JOIN companies c ON s.ticker=c.ticker WHERE c.sector=?", (db_sector,))
    avg_spi = cursor.fetchone()[0] or 0
    
    macro_row = cursor.execute("SELECT * FROM financing_macro ORDER BY date DESC LIMIT 1").fetchone()
    macro = dict(macro_row) if macro_row else {}
    conn.close()
    
    context = {
        "macro": macro,
        "aggregates": {"avg_spi": round(avg_spi, 1), "sector": sector},
        "top_drivers": []
    }
    
    result = brief_service.generate_brief(sector, sub_industry, context, force_refresh=force)
    return jsonify(result)

# --- DOSSIER ENDPOINT ---
@app.route('/api/company-dossier', methods=['POST'])
def company_dossier():
    req = request.json
    ticker = req.get('ticker')
    force = req.get('force_refresh', False)
    
    if not ticker: 
        return jsonify({"error": "No ticker provided"})
    
    context_payload = retrieval_service.retrieve_context(ticker)
    result = dossier_service.generate_dossier(ticker, context_payload, force_refresh=force)
    return jsonify(result)


# --- DEAL ARCHITECT v1.1 ROUTES ---

@app.route('/deal-architect')
def deal_architect_page():
    return render_template('deal_architect.html', active_page='architect')





# --- DEAL COMMAND v2.1 ROUTES ---


@app.route('/deal-command')
def deal_command():
    return render_template('deal_command.html', active_page='command')

@app.route('/help')
def help_page():
    return render_template('help.html', active_page='help')

@app.route('/api/v2/market-map')
def v2_market_map():
    sector = request.args.get('sector', 'Tech')
    db_sector = 'Technology' if sector == 'Tech' else sector
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if extended columns exist in companies table
    # We try to select them; if not present, we get None/Error. 
    # For stability, we select standard columns and separate query or join if needed.
    # Assuming standard columns for now and we will calculate what we can or mock unavailable ones 
    # based on the prompt's "N/A" fallback. 
    # Ideally we'd join with a 'fundamentals' table if it existed.
    
    query = """
        SELECT c.ticker, c.company_name, c.market_cap, c.sub_sector,
               s.spi, s.buyer_readiness, s.capacity, 
               s.spi_drivers_json, s.br_drivers_json
        FROM companies c
        JOIN scores s ON c.ticker = s.ticker
        WHERE c.sector = ?
        ORDER BY s.spi DESC
    """
    try:
        cursor.execute(query, (db_sector,))
        rows = cursor.fetchall()
    except:
        # Fallback if sub_sector missing
        query = """
            SELECT c.ticker, c.company_name, c.market_cap,
                   s.spi, s.buyer_readiness, s.capacity, 
                   s.spi_drivers_json, s.br_drivers_json
            FROM companies c
            JOIN scores s ON c.ticker = s.ticker
            WHERE c.sector = ?
            ORDER BY s.spi DESC
        """
        cursor.execute(query, (db_sector,))
        rows = cursor.fetchall()

    conn.close()
    
    sellers = []
    buyers = []
    
    # Helper to clean firepower
    def parse_firepower(val, cap):
        if not val: return 0.0
        try:
             fp = float(val)
             # Sanity check: Firepower > 10x Market Cap is suspicious (unless micro cap)
             if cap and fp > (cap * 10) and cap > 1e9: 
                 return 0.0 # Anomaly
             return fp
        except:
            return 0.0

    # Helper for Seller Confidence
    def get_confidence_and_type(driver_str, spi):
        stype = "Opportunistic"
        conf = "Low"
        emoji = ""
        
        if any(x in driver_str for x in ["🔥", "Forced", "Distress", "Bankruptcy"]):
            stype = "Forced Seller"
            emoji = "🔥"
            conf = "High"
        elif "Strategic Review" in driver_str or "📉" in driver_str:
            stype = "Strategic Review"
            emoji = "📉"
            conf = "High" if spi > 80 else "Med"
        elif spi > 75:
             stype = "High Potential"
             conf = "Med"
             
        return stype, emoji, conf

    import random # Mocking financial metrics as they aren't in the DB query result yet
    
    for r in rows:
        row_dict = dict(r)
        
        try:
            spi_d = json.loads(row_dict['spi_drivers_json']) if row_dict['spi_drivers_json'] else []
            br_d = json.loads(row_dict['br_drivers_json']) if row_dict['br_drivers_json'] else []
        except:
            spi_d, br_d = [], []
        
        base_obj = {
            "ticker": row_dict['ticker'],
            "name": row_dict['company_name'],
            "sub_sector": row_dict.get('sub_sector', sector),
            "market_cap": row_dict['market_cap']
        }
        
        # --- Supply Logic ---
        if row_dict['spi'] >= 20:
            # Deterministic Seller Type from Drivers
            full_driver_str = " ".join([str(d) for d in spi_d])
            s_type, s_emoji, s_conf = get_confidence_and_type(full_driver_str, row_dict['spi'])
            
            # Simulated Financials (Replace with real DB columns when available)
            # Logic: We use SPI to loosely correlate for realism if data missing
            m_cap = row_dict['market_cap'] or 1e9
            
            # Net Leverage: Higher for Forced/Distressed
            sim_lev = round(random.uniform(4.0, 7.0), 1) if "Forced" in s_type else round(random.uniform(1.5, 3.5), 1)
            
            # Price Dislocation: Higher for distressed
            sim_disc = round(random.uniform(30, 60)) if "Forced" in s_type else round(random.uniform(5, 25))
            
            # Enhanced Driver Formatting
            drivers_fmt = []
            if "Forced" in s_type: drivers_fmt.append(f"Lev: {sim_lev}x")
            if "Distress" in s_type: drivers_fmt.append("Liquidity < 6m")
            if spi_d: drivers_fmt.extend([str(d).replace("TYPE:","").strip() for d in spi_d[:2]])

            sellers.append({
                **base_obj,
                "spi": int(row_dict['spi']),
                "seller_type": s_type,
                "seller_emoji": s_emoji,
                "confidence": s_conf,
                "metrics": {
                    "net_leverage": f"{sim_lev}x",
                    "price_dislocation": f"-{sim_disc}%",
                    "interest_coverage": "2.1x" if sim_lev < 4 else "0.8x",
                    "debt_maturity": "2026"
                },
                "likely_asset_type": "WholeCo" if m_cap < 5e9 else "Carve-out",
                "catalyst_badge": "Earnings Miss" if sim_disc > 20 else "Strategic Review",
                "drivers": drivers_fmt[:3], # Top 3 Numeric/Text Mixed
                "all_drivers": [str(d) for d in spi_d]
            })
        
        # --- Demand Logic ---
        if row_dict['buyer_readiness'] >= 20:
            fp_val = parse_firepower(row_dict['capacity'], row_dict['market_cap'])
            
            # Mandate extraction
            mandate = "Growth"
            for d in br_d:
                 if "Targeting:" in str(d):
                     mandate = str(d).replace("Targeting:", "").strip()
                     break
            
            buyers.append({
                **base_obj,
                "br": int(max(0, min(100, row_dict['buyer_readiness']))), # Clamp 0-100
                "firepower": fp_val, # Raw USD
                "mandate": mandate,
                "drivers": [str(d) for d in br_d],
                "is_anomaly": True if (fp_val > (row_dict['market_cap'] * 2) and row_dict['market_cap'] > 1e9) else False
            })
    
    # Filter anomalies from default list
    buyers = [b for b in buyers if not b.get('is_anomaly', False)]
    
    sellers.sort(key=lambda x: x['spi'], reverse=True)
    buyers.sort(key=lambda x: x['br'], reverse=True)
    
    # --- PINNED TICKER LOGIC (SSNC) ---
    def pin_ticker(data_list, ticker, default_obj=None):
        idx = next((i for i, item in enumerate(data_list) if item["ticker"] == ticker), -1)
        if idx != -1:
            item = data_list.pop(idx)
            data_list.insert(0, item)
        elif default_obj:
            data_list.insert(0, default_obj)
        return data_list

    # Mock SSNC with numeric drivers
    ssnc_seller = {
        "ticker": "SSNC", "name": "SS&C Technologies", "sub_sector": "Software", "market_cap": 16e9,
        "spi": 88, "seller_type": "Strategic Review", "seller_emoji": "📉", "confidence": "High",
        "metrics": {"net_leverage": "4.2x (High)", "interest_coverage": "2.5x", "price_dislocation": "-12%"}, 
        "drivers": ["Activists (13D)", "Margin Pressure (-200bps)", "Portfolio Ops"],
        "all_drivers": ["Activists (13D)", "Margin Pressure (-200bps)", "Portfolio Ops"],
        "likely_asset_type": "Carve-out (FinTech)",
        "catalyst_badge": "13D Filing"
    }
    
    ssnc_buyer = {
        "ticker": "SSNC", "name": "SS&C Technologies", "sub_sector": "Software", "market_cap": 16e9,
        "br": 92, "firepower": 4500000000.0, "mandate": "Vertical Software", 
        "drivers": ["Consolidator", "High FCF", "Recurring Revenue"]
    }

    sellers = pin_ticker(sellers, "SSNC", ssnc_seller)
    buyers = pin_ticker(buyers, "SSNC", ssnc_buyer)
    
    # --- SELLER PLAYBOOK GENERATION ---
    # Bucket sellers into archetypes
    archetypes = {
        "Refinancing-Driven": {"count": 0, "examples": [], "desc": "Maturity wall < 18m or Lev > 5x"},
        "Price-Distress": {"count": 0, "examples": [], "desc": "Dislocation > 30% + Stable Assets"},
        "Activist-Driven": {"count": 0, "examples": [], "desc": "13D Filings or Strategic Review"},
        "Growth-Stall": {"count": 0, "examples": [], "desc": "Rev Growth < 0% + Comp Pressure"}
    }
    
    for s in sellers:
        # Simple heuristic classification
        d_str = " ".join(s.get('all_drivers', []))
        is_matched = False
        
        if "Maturity" in d_str or "Leverage" in d_str:
            archetypes["Refinancing-Driven"]["count"] += 1
            is_matched = True
        if "Dislocation" in d_str or "Price" in d_str:
            archetypes["Price-Distress"]["count"] += 1
            is_matched = True
        if "Activist" in d_str or "Review" in d_str:
            archetypes["Activist-Driven"]["count"] += 1
            is_matched = True
        
        # Default bucket
        if not is_matched and s['spi'] > 60:
             archetypes["Growth-Stall"]["count"] += 1

    # Format Playbook for Frontend
    top_archetypes = sorted(
        [{"name": k, "count": v["count"], "desc": v["desc"]} for k,v in archetypes.items()], 
        key=lambda x: x['count'], reverse=True
    )[:3]

    playbook = {
        "top_archetypes": top_archetypes,
        "watchlist": [
            {"label": "HY Spreads > 500bps", "status": "Stable", "impact": "High"},
            {"label": "Sponsor Dry Powder", "status": "deployed", "impact": "Medium"}
        ],
        "actions": [
            "Screen for spin-off candidates in 'Activist' bucket",
            "Pitch private credit recap for 'Refinancing' targets",
            "Refresh buy-side mandates for 'Price-Distress' assets"
        ]
    }

    return jsonify({"sellers": sellers[:500], "buyers": buyers[:500], "playbook": playbook})

@app.route('/api/v2/deal-tape')
def v2_deal_tape():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals ORDER BY announced_date DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "date": r['announced_date'], "acquirer": r['acquirer_ticker'], "target": r['target_ticker'],
        "status": r['status'], "type": r['deal_type'], "url": r['source_url']
    } for r in rows])

@app.route('/api/v2/sponsors')
def v2_sponsors():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sponsors")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "name": r['name'], "powder": r['est_dry_powder_usd'], "note": r['source_note'], "updated": r['last_updated']
    } for r in rows])

@app.route('/api/v2/diagnostics')
def v2_diagnostics():
    conn = get_db()
    cursor = conn.cursor()
    stats = {}
    stats['total_companies'] = cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    stats['scored_count'] = cursor.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
    stats['deal_count'] = cursor.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
    stats['event_count'] = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    unknown = cursor.execute("SELECT COUNT(*) FROM companies WHERE sector = 'Unknown'").fetchone()[0]
    stats['unknown_pct'] = round((unknown / stats['total_companies'] * 100), 1) if stats['total_companies'] > 0 else 0
    conn.close()
    return jsonify(stats)

@app.route('/api/v2/financing')
def v2_financing():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financing_macro ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "hy_spread": row['hy_spread'],
            "ig_spread": row['ig_spread'],
            "lbo_idx": row['lbo_feasibility_index'],
            "lev_range": row['expected_leverage_range']
        })
    return jsonify({"hy_spread": 0, "lbo_idx": 0, "lev_range": "--"})

@app.route('/api/v2/matches')
def v2_matches():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches ORDER BY fit_score DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        "buyer": r['company_ticker'],
        "target": r['counterparty_ticker'],
        "score": int(r['fit_score']),
        "drivers": json.loads(r['drivers_json']),
        "pair": f"{r['company_ticker']}-{r['counterparty_ticker']}"
    } for r in rows])


@app.route('/api/v2/deep-dive', methods=['POST'])
def v2_deep_dive():
    data = request.json
    ticker = data.get('ticker')
    type_ = data.get('type')
    context = data.get('context', {})
    
    # Lazy import to avoid circular dep if any
    from src.analysis.gemini_deep_dive import analyze_company
    
    html_result = analyze_company(ticker, type_, context)
    return jsonify({'html': html_result})

@app.route('/api/v2/sector-brief', methods=['POST'])
def v2_sector_brief():
    data = request.json
    sector = data.get('sector')
    res = brief_service.generate_deal_command_brief(
        sector=sector,
        financing_data=data.get('financing', {}),
        top_sellers=data.get('top_sellers', []),
        top_buyers=data.get('top_buyers', [])
    )
    return jsonify(res)

@app.route('/api/tickers', methods=['GET'])
def api_search_tickers():
    """Returns a list of tickers/names for autocomplete."""
    query = request.args.get('q', '').lower()
    from src.data.universe_service import UniverseService
    svc = UniverseService()
    
    results = []
    count = 0
    for c in svc.universe:
        t = c.get('ticker', '').lower()
        n = c.get('title', '').lower()
        if not t: continue
        
        if query in t or query in n:
            results.append({
                "ticker": c['ticker'],
                "name": c.get('title') or c.get('short_name'),
                "sector": c.get('sector', 'Unknown'),
                "industry": c.get('sub_industry', 'Unknown'),
                "market_cap": c.get('market_cap', 0)
            })
            count += 1
            if count >= 20: break
    return jsonify(results)




# --- Deal Architect Routes (Consolidated) ---

@app.route('/api/deal-architect/match', methods=['POST'])
def api_deal_match():
    """Rank candidates with Banker Logic + AI Batch Analysis."""
    data = request.json
    user_ticker = data.get('user_ticker', 'CVS')
    intent = data.get('intent', 'BUY')
    mandate = data.get('mandate', 'Adjacency')
    include_ai = data.get('include_ai', False)
    
    # 1. Profile & Universe
    from src.data.universe_service import UniverseService
    from src.analysis.matchmaker import MatchEngine # Ensure import
    
    user_profile = build_user_profile(user_ticker)
    
    # 2. Banker Logic
    engine = MatchEngine() # No args in new class
    # Returns List[MatchCandidate]
    candidates = engine.find_matches(user_profile, intent, mandate)
    
    # Convert dataclasses to dicts
    matches = [c.to_dict() for c in candidates]
    
    # 3. AI Batch (Consolidated Service)
    ai_insights = {}
    if include_ai and matches:
        top_matches = matches[:10] # Batch limit
        ai_insights = brief_service.analyze_match_batch(
            user_profile={"ticker": user_profile.ticker, "name": user_profile.business_summary},
            candidates=top_matches,
            intent=intent
        )
        
        # Re-Rank based on AI Fit Score (User Request)
        if ai_insights:
            for m in top_matches:
                t = m.get('ticker')
                if t in ai_insights:
                    m['ai_fit_score'] = ai_insights[t].get('fit_score', 0)
            
            # Sort top 10 by AI Score descending
            top_matches.sort(key=lambda x: x.get('ai_fit_score', 0), reverse=True)
            # Reconstruct matches list with re-ranked top 10
            matches = top_matches + matches[10:]
            
    return jsonify({
        "matches": matches,
        "ai_batch": ai_insights
    })

@app.route('/api/deal-architect/deep-dive', methods=['POST'])
def api_deep_dive():
    """Live Deep Dive using Consolidated Service."""
    data = request.json
    user_ticker = data.get('user_ticker')
    target_ticker = data.get('target_ticker')
    intent = data.get('intent', 'BUY')
    mandate = data.get('mandate', 'Adjacency')
    
    # 1. Live Data & Calc
    try:
        result = perform_live_dossier(user_ticker, target_ticker, intent, mandate)
        
        # 2. AI Memo (Consolidated Service)
        memo = brief_service.generate_live_deal_memo(
            user=result['user'],
            candidate=result['candidate'],
            intent=intent,
            mandate_mode=mandate,
            metric_data={"metrics": result['metrics'], "scores": result['scores']},
            macro=result['macro'],
            headlines=result.get('headlines', '') # Fixed key usage
        )
        
        print(f"DEBUG MEMO KEYS: {memo.keys()}")
        
        response_payload = {
            "metrics": result['metrics'],
            "scores": result['scores'],
            "macro": result['macro'],
            "memo_html": memo.get('html', "<b>Error: Missing HTML key</b>"), # Safety fallback
            "verdict": memo.get('verdict', {}),
            "recency_audit": memo.get('recency_audit', {}),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        print(f"DEBUG RESPONSE KEYS: {response_payload.keys()}")
        
        return jsonify(response_payload)
    except Exception as e:
        print(f"ERROR in api_deal_match: {e}")
        return jsonify({
            "error": str(e),
            "memo_html": f"<div class='alert alert-danger'>System Error: {str(e)}</div>",
            "verdict": {"status": "ERROR"},
            "metrics": {},
            "scores": {},
            "macro": {}
        })

if __name__ == '__main__':
    print("Starting M&A Health Forecast Platform (v2.3 Deal Architect)...")
    if not os.path.exists(get_db_path()):
        print("Database not found. Please run init_db.py first.")
    
    # Reload trigger 8
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
