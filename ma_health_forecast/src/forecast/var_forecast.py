import pandas as pd
import numpy as np
from statsmodels.tsa.api import VAR

def forecast_with_var(bucket_scores: pd.DataFrame, steps: int = 12):
    """
    Fits a VAR model to the historical bucket scores and generates a forecast.
    
    Assumes input data (bucket_scores) is stationary (which normalized scores typically are).
    """
    # 1. Initialize the model
    model = VAR(bucket_scores)

    # 2. Select optimal lag order using AIC (Akaike Information Criterion)
    # Constrain maxlags to avoid overfitting (e.g., 12 for monthly data)
    try:
        lag_order_results = model.select_order(maxlags=12)
        optimal_lag = lag_order_results.aic
    except Exception as e:
        print(f"Warning: VAR lag selection failed ({e}). Defaulting to 4.")
        optimal_lag = 4 

    # 3. Fit the model
    print(f"Fitting VAR model with lag order: {optimal_lag}")
    var_results = model.fit(optimal_lag)

    # 4. Forecast
    # VAR requires the last 'optimal_lag' observations to project forward
    lagged_values = bucket_scores.values[-optimal_lag:]
    forecast = var_results.forecast(y=lagged_values, steps=steps)

    # 5. Format output
    # Ensure we have a valid date index for the forecast
    last_date = bucket_scores.index[-1]
    forecast_dates = pd.date_range(start=last_date, periods=steps + 1, freq='ME')[1:]
    
    forecast_df = pd.DataFrame(forecast, index=forecast_dates, columns=bucket_scores.columns)

    # The composite forecast is the sum of the already weighted bucket forecasts
    # Assuming the input bucket_scores are already weighted. If not, apply weights here.
    forecast_df['Composite_Index'] = forecast_df.sum(axis=1)

    return forecast_df, var_results
