import pandas as pd
import numpy as np
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class FredLoader:
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment variables.")
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    def fetch_series(self, series_id: str, start: str = "2010-01-01") -> pd.Series:
        """
        Fetch real time series data from FRED API with Caching (24h).
        """
        # Cache Path
        cache_dir = os.path.join(os.path.dirname(__file__), 'store', 'fred')
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except OSError:
                pass # concurrency safety

        cache_file = os.path.join(cache_dir, f"{series_id}.csv")
        
        # 1. Try Cache
        if os.path.exists(cache_file):
            try:
                # Check 24h freshness
                mtime = os.path.getmtime(cache_file)
                if (time.time() - mtime) < 86400:
                    print(f"  [Cache hit] Loading {series_id}...")
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    # CSV load might lose serie name
                    df = df["value"]
                    df.name = series_id
                    return df
            except Exception as e:
                print(f"  Result: Cache corrupted for {series_id} ({e}), refetching...")

        # 2. Fetch API
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": start,
        }
        
        try:
            print(f"  [API Fetch] Downloading {series_id}...")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            observations = data.get("observations", [])
            if not observations:
                print(f"Warning: No observations found for {series_id}")
                return pd.Series(dtype=float, name=series_id)

            df = pd.DataFrame(observations)
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            
            # Save to Cache
            try:
                # Save just the value column with date index
                save_df = df.set_index("date")[["value"]] 
                save_df.to_csv(cache_file)
            except Exception as e:
               print(f"  Warning: Could not write cache for {series_id}: {e}")

            df = df.set_index("date")["value"]
            df.name = series_id
            return df
            
        except Exception as e:
            print(f"Error fetching {series_id}: {e}")
            raise e

def fetch_series(series_id: str, start: str = "2010-01-01") -> pd.Series:
    loader = FredLoader()
    return loader.fetch_series(series_id, start)

def to_monthly(s: pd.Series, how: str) -> pd.Series:
    # Resample to monthly end and apply aggregation
    return s.resample("ME").agg(how)

def load_series(series_id: str, agg: str, start: str) -> pd.Series:
    print(f"Fetching {series_id} from FRED...")
    raw = fetch_series(series_id, start=start)
    return to_monthly(raw, how=agg)
