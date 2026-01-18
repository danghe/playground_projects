
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from analysis.strategic_radar import scan_sector_audit
from data.universe_service import UniverseService

def verify():
    print("--- Verifying Deal Radar Logic ---")
    
    # 1. Clear Cache to force logic run (if any)
    # Actually, scan_sector_audit uses cache if present. 
    # We want to see the RESULT of the logic.
    # If the cache was just built by a previous run (it wasn't, only ingestion was run),
    # then scan_sector_audit will build it now.
    
    # Force delete cache to be sure we test logic
    cache_path = os.path.join(os.getcwd(), 'src', 'data', 'store', 'radar', 'radar_tech.json')
    if os.path.exists(cache_path):
        os.remove(cache_path)
        print("Cleared Radar Cache.")
        
    print("Running Scan for 'Tech'...")
    results, heatmap, narrative, playbook = scan_sector_audit('Tech')
    
    print(f"\nResults: {len(results)} companies")
    
    # 2. Check Taxonomy
    subs = set(r.get('sub_industry') for r in results)
    print(f"Sub-Industries Found: {subs}")
    if "Semiconductors" in subs or "Hardware" in subs:
        print("✅ Taxonomy working (Detailed Tech sub-industries found)")
    else:
        print("❌ Taxonomy failed (Only generic buckets found?)")
        
    # 3. Check Firepower
    valid_fp = 0
    zero_fp = 0
    na_fp = 0
    
    for r in results:
        fp = r['evidence']['firepower']
        if fp == "N/A":
            na_fp += 1
        elif fp == "$0.0B":
            zero_fp += 1
        else:
            valid_fp += 1
            
    print(f"Firepower Stats: Valid={valid_fp}, Zero={zero_fp}, N/A={na_fp}")
    if valid_fp > 0:
        print("✅ Firepower computation active.")
    else:
        print("⚠️ Warning: No valid Firepower found.")

    # 4. Check Valuation
    valid_val = 0
    for r in results:
        val = r['evidence'].get('ev_ebitda', 'N/A')
        if val != "N/A":
            valid_val += 1
            
    print(f"Valuation Stats: Valid={valid_val}/{len(results)}")
    
    # 5. Check Drivers
    drivers_count = 0
    for r in results:
        drivers = r['evidence'].get('top_drivers', [])
        if drivers:
            drivers_count += 1
            # Check structure
            if 'label' not in drivers[0] or 'type' not in drivers[0]:
                print(f"❌ Driver structure mismatch: {drivers[0]}")
    
    print(f"Companies with Drivers: {drivers_count}")

if __name__ == "__main__":
    verify()
