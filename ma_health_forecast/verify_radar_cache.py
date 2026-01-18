from src.analysis.strategic_radar import scan_sector_audit
import time
import os
import shutil

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'data', 'store', 'radar')

def clear_cache(sector):
    """Clear specific sector cache for testing."""
    filename = f"radar_{sector.lower()}.json"
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Cleared cache for {sector}")
        except Exception as e:
            print(f"Failed to clear cache: {e}")

def verify_caching():
    sector = "Tech"
    
    # 1. Clear Cache to force fresh scan
    clear_cache(sector)
    
    print("\n--- RUN 1: Fresh Scan (Should be slow) ---")
    start_time = time.time()
    results1, _, _, _ = scan_sector_audit(sector)
    duration1 = time.time() - start_time
    print(f"Run 1 completed in {duration1:.2f} seconds.")
    print(f"Companies found: {len(results1)}")
    
    # Verify cache file exists
    cache_file = os.path.join(CACHE_DIR, f"radar_{sector.lower()}.json")
    if os.path.exists(cache_file):
        print(f"SUCCESS: Cache file created at {cache_file}")
    else:
        print(f"FAILURE: Cache file NOT found at {cache_file}")
        return

    # 2. Run Again (Should be fast)
    print("\n--- RUN 2: Cached Scan (Should be fast) ---")
    start_time = time.time()
    results2, _, _, _ = scan_sector_audit(sector)
    duration2 = time.time() - start_time
    print(f"Run 2 completed in {duration2:.2f} seconds.")
    print(f"Companies found: {len(results2)}")
    
    # Verify Speedup
    if duration2 < 1.0 and duration2 < duration1:
        print(f"\nSUCCESS: Caching is working! Speedup factor: {duration1/duration2:.1f}x")
    else:
        print(f"\nWARNING: Run 2 was not significantly faster ({duration2:.2f}s). Check logic.")

if __name__ == "__main__":
    verify_caching()
