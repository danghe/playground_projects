import sys
import os
from dotenv import load_dotenv
from src.data.fred_loader import FredLoader

load_dotenv()

print("Testing FRED API Connectivity...")
try:
    loader = FredLoader()
    print(f"API Key found: {loader.api_key[:5]}...")
    
    # Try fetching a simple series (e.g., GDP or a rate)
    series_id = "BAMLH0A0HYM2" # High Yield Index used in the app
    print(f"Fetching {series_id}...")
    data = loader.fetch_series(series_id, start="2023-01-01")
    
    if not data.empty:
        print(f"SUCCESS: Fetched {len(data)} observations.")
        print(data.head())
    else:
        print("WARNING: Fetched data is empty.")
        
except Exception as e:
    print(f"FAILURE: FRED API Test failed: {e}")
