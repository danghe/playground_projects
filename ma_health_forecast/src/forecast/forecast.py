import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

def arima_forecast(series: pd.Series, steps: int = 12, order=(3, 0, 0)):
    series = series.dropna()
    model = ARIMA(series, order=order, enforce_stationarity=False, enforce_invertibility=False)
    res = model.fit()
    fc = res.get_forecast(steps=steps)
    df_fc = fc.summary_frame(alpha=0.2).rename(columns={"mean": "forecast", "mean_ci_lower": "lower80", "mean_ci_upper": "upper80"})
    conf95 = res.get_forecast(steps=steps).conf_int(alpha=0.05)
    df_fc["lower95"] = conf95.iloc[:, 0].values
    df_fc["upper95"] = conf95.iloc[:, 1].values
    return df_fc, res
