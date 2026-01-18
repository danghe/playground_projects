import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

# Load custom style
style_path = Path(__file__).parent / "style.mplstyle"
if style_path.exists():
    plt.style.use(str(style_path))

def plot_composite(df: pd.DataFrame, path: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Regime Background
    ax.axhspan(50, 100, color='green', alpha=0.05, label='Expansionary')
    ax.axhspan(0, 50, color='red', alpha=0.05, label='Contractionary')
    
    # Plot raw index
    df["Composite"].plot(ax=ax, label="M&A Health Index", color="#005587", linewidth=2.5)
    
    # Add Trend Line (12-month rolling average)
    df["Composite"].rolling(12).mean().plot(ax=ax, label="12-Month Trend", color="#FFB81C", linewidth=2, linestyle="--")
    
    ax.set_title("M&A Health Index: Historical Performance", pad=20, fontweight='bold')
    ax.set_ylabel("Index Value (0-100)")
    ax.set_xlabel("")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left", frameon=True)
    
    # Add latest value annotation
    latest_val = df["Composite"].iloc[-1]
    latest_date = df.index[-1]
    ax.annotate(f"{latest_val:.1f}", 
                xy=(latest_date, latest_val), 
                xytext=(10, 0), 
                textcoords="offset points", 
                verticalalignment="center",
                fontweight="bold", color="#005587")

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_buckets(df: pd.DataFrame, path: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    cols = [c for c in df.columns if c.startswith("BKT_")]
    
    # Define color mapping
    color_map = {
        "Deal Activity": "#D32F2F",  # Strong Red
        "Credit": "#1f77b4",         # Blue
        "Rates Curve": "#ff7f0e",    # Orange
        "Equity Vol": "#9467bd",     # Purple
        "Macro": "#2ca02c",          # Green
        "Liquidity Issuance": "#17becf" # Teal
    }
    
    # Simplify column names for legend
    labels = [c.replace("BKT_", "").replace("_", " ").title() for c in cols]
    
    # Get colors in order of columns
    plot_colors = [color_map.get(label, "#333333") for label in labels]
    
    df[cols].plot(ax=ax, linewidth=1.5, alpha=0.8, color=plot_colors)
    
    ax.legend(labels, bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)
    ax.set_title("Component Contributions (Z-Scores)", pad=20, fontweight='bold')
    ax.set_ylabel("Contribution (Std Dev)")
    ax.set_xlabel("")
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_forecast(history: pd.Series, fc: pd.DataFrame, path: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot History (Last 5 years only for clarity)
    plot_start = history.index[-60] if len(history) > 60 else history.index[0]
    hist_subset = history[plot_start:]
    
    hist_subset.plot(ax=ax, label="Historical Data", color="#005587", linewidth=2.5)
    
    # Plot Forecast
    fc["forecast"].plot(ax=ax, label="Forecast", color="#FFB81C", linewidth=2.5, linestyle="--")
    
    # Confidence Intervals
    ax.fill_between(fc.index, fc["lower80"], fc["upper80"], color="#FFB81C", alpha=0.2, label="80% Confidence")
    
    # Vertical line at forecast start
    ax.axvline(x=history.index[-1], color="gray", linestyle=":", alpha=0.5)
    
    ax.set_title("12-Month M&A Health Forecast", pad=20, fontweight='bold')
    ax.set_ylabel("Index Value")
    ax.set_xlabel("")
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left", frameon=True)
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_dashboard(df: pd.DataFrame, fc: pd.DataFrame, path: str):
    """
    Create a 2x2 dashboard summary.
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2)
    
    # 1. Main Index + Forecast (Top Left)
    ax1 = fig.add_subplot(gs[0, 0])
    # Combine history and forecast for a continuous line
    hist_subset = df["Composite"].iloc[-48:] # Last 4 years
    hist_subset.plot(ax=ax1, label="History", color="#005587", linewidth=2)
    fc["forecast"].plot(ax=ax1, label="Forecast", color="#FFB81C", linestyle="--", linewidth=2)
    ax1.fill_between(fc.index, fc["lower80"], fc["upper80"], color="#FFB81C", alpha=0.15)
    ax1.set_title("M&A Health Outlook", fontweight="bold")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.2)
    
    # 2. Current Drivers (Top Right) - Bar Chart of latest bucket values
    ax2 = fig.add_subplot(gs[0, 1])
    latest_buckets = df[[c for c in df.columns if c.startswith("BKT_")]].iloc[-1]
    latest_buckets.index = [c.replace("BKT_", "").replace("_", " ").title() for c in latest_buckets.index]
    colors = ['#2ca02c' if x >= 0 else '#d62728' for x in latest_buckets.values]
    latest_buckets.plot(kind='barh', ax=ax2, color=colors, alpha=0.8)
    ax2.set_title("Current Drivers (Z-Score)", fontweight="bold")
    ax2.axvline(0, color='black', linewidth=0.5)
    
    # 3. Key Risk Indicators (Bottom Left) - VIX and Spreads (if available)
    ax3 = fig.add_subplot(gs[1, 0])
    # Assuming these columns exist or we can approximate from buckets if raw series aren't passed
    # For now, let's plot the "Credit" and "Equity Vol" buckets as proxies
    if "BKT_credit" in df.columns and "BKT_equity_vol" in df.columns:
        df["BKT_credit"].iloc[-48:].plot(ax=ax3, label="Credit Stress (Inv)", color="#d62728")
        df["BKT_equity_vol"].iloc[-48:].plot(ax=ax3, label="Market Fear (Inv)", color="#9467bd")
        ax3.set_title("Risk Indicators (Inverted)", fontweight="bold")
        ax3.legend()
        ax3.grid(True, alpha=0.2)
    else:
        ax3.text(0.5, 0.5, "Risk Data Unavailable", ha='center')
        
    # 4. Year-over-Year Change (Bottom Right)
    ax4 = fig.add_subplot(gs[1, 1])
    yoy = df["Composite"].diff(12).iloc[-48:]
    colors_yoy = ['#2ca02c' if x >= 0 else '#d62728' for x in yoy.values]
    ax4.bar(yoy.index, yoy.values, color=colors_yoy, width=20, alpha=0.6) # width in days approx
    ax4.set_title("Year-over-Year Momentum", fontweight="bold")
    ax4.axhline(0, color='black', linewidth=0.5)
    ax4.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
