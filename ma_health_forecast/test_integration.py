import sys
import os
from dotenv import load_dotenv
import pandas as pd
from src.forecast.llm_forecast import gemini_forecast

load_dotenv()

# Mock data
dates = pd.date_range(start='2023-01-01', periods=24, freq='M')
values = [50 + i%5 for i in range(24)]
history = pd.Series(values, index=dates)

print("Testing Gemini Forecast Integration...")
try:
    df, rationale = gemini_forecast(history, steps=12, rate_shock=-50, credit_stress=5)
    print("\nForecast DataFrame Head:")
    print(df.head())
    print("\nRationale Preview:")
    print(rationale[:200] + "...")
    print("\nSUCCESS: Integration test passed.")
except Exception as e:
    print(f"\nFAILURE: Integration test failed with error: {e}")
