from src.data.fred_loader import load_series
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'data', 'store', 'fred')

def clear_cache(series_id):
    filename = f"{series_id}.csv"
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Cleared cache for {series_id}")
        except Exception as e:
            print(f"Failed to clear cache: {e}")

def verify():
    series_id = "UNRATE" # Unemployment Rate
    
    # 1. Clear Cache
    clear_cache(series_id)
    
    print("\n--- RUN 1: API Fetch (Should be slow) ---")
    start = time.time()
    try:
        s1 = load_series(series_id, agg="mean", start="2020-01-01")
        print(f"Run 1 loaded {len(s1)} points.")
    except Exception as e:
        print(f"Run 1 Failed: {e}")
        return

    dur1 = time.time() - start
    print(f"Run 1 time: {dur1:.2f}s")
    
    # Check File
    cache_file = os.path.join(CACHE_DIR, f"{series_id}.csv")
    if os.path.exists(cache_file):
        print(f"SUCCESS: Cache file exists at {cache_file}")
    else:
        print("FAILURE: Cache file not created.")
        
    print("\n--- RUN 2: Cache Hit (Should be fast) ---")
    start = time.time()
    s2 = load_series(series_id, agg="mean", start="2020-01-01")
    dur2 = time.time() - start
    print(f"Run 2 time: {dur2:.2f}s")
    
    if dur2 < 0.2:
        print(f"\nSUCCESS: Caching works! Speedup: {dur1/dur2:.1f}x")
    else:
        print("\nWARNING: Cache might not be working efficiently.")

if __name__ == "__main__":
    verify()
