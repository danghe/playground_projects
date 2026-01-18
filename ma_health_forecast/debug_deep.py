import json
import os
import glob
from datetime import datetime

BASE_DIR = r"d:\00Intralinks\M&A Forecast Project\ma_health_forecast_project\ma_health_forecast"
STORE_DIR = os.path.join(BASE_DIR, "src", "data", "store")
RADAR_CACHE_DIR = os.path.join(STORE_DIR, "radar")
YF_CACHE_DIR = os.path.join(BASE_DIR, "src", "data", "cache")

def check_radar_cache():
    print("--- 1. Checking Radar Cache (UI Source) ---")
    files = glob.glob(os.path.join(RADAR_CACHE_DIR, "radar_*.json"))
    for f_path in files:
        print(f"File: {os.path.basename(f_path)}")
        try:
            with open(f_path, 'r') as f:
                data = json.load(f)
            
            payload_data = data.get('payload', [])
            if isinstance(payload_data, list) and len(payload_data) > 0:
                 # Legacy format? Payload is tuple (results, heatmap, ...)
                 # The code says: payload = (results, heatmap, ...)
                 # So payload is a list/tuple of 4 items.
                 results = payload_data[0]
                 print(f"  Count: {len(results)} targets")
                 
                 # Check SSNC in results
                 ssnc = next((r for r in results if r['ticker'] == 'SSNC'), None)
                 if ssnc:
                     print(f"  [SSNC] Found in Radar Cache")
                     print(f"    Scores: {ssnc.get('scores')}")
                     print(f"    Evidence: {ssnc.get('evidence')}")
                     print(f"    EBITDA: {ssnc.get('ev_ebitda')}")
                     print(f"    Firepower: {ssnc.get('firepower_raw')}")
                 else:
                     print(f"  [SSNC] NOT FOUND in Radar Cache results!")

                 # Check Coverage (Giants)
                 giants = ['CRM', 'ADBE', 'ORCL', 'SAP', 'NVDA']
                 found_giants = [g for g in giants if any(r['ticker'] == g for r in results)]
                 print(f"  [Giants] Found: {found_giants} / {giants}")

            else:
                print("  Payload format unknown or empty.")
        except Exception as e:
            print(f"  Error reading: {e}")

def check_fundamentals_store():
    print("\n--- 2. Checking Fundamentals Store (Ingestion Source) ---")
    f_path = os.path.join(STORE_DIR, 'fundamentals.json')
    try:
        with open(f_path, 'r') as f:
            data = json.load(f)
        
        ssnc = data.get('SSNC')
        if ssnc:
             print(f"  [SSNC] Found in Store")
             print(f"    Market Cap: {ssnc.get('market_cap')}")
             print(f"    EBITDA: {ssnc.get('ebitda')}")
             print(f"    Cash: {ssnc.get('total_cash')}")
             print(f"    Debt: {ssnc.get('total_debt')}")
        else:
             print(f"  [SSNC] NOT FOUND in Fundamentals Store")

    except Exception as e:
        print(f"  Error reading store: {e}")

def check_yf_cache():
    print("\n--- 3. Checking YF Cache (Analysis Source) ---")
    files = glob.glob(os.path.join(YF_CACHE_DIR, "SSNC_fund.json"))
    if files:
        f_path = files[0]
        print(f"  Found Cache: {f_path}")
        try:
            with open(f_path, 'r') as f:
                data = json.load(f)
            print(f"    Market Cap: {data.get('market_cap')}")
            print(f"    EBITDA: {data.get('ebitda')}")
        except Exception as e:
            print(f"    Error reading: {e}")
    else:
        print("  SSNC_fund.json NOT FOUND in YF Cache")

def check_universe_coverage():
    print("\n--- 4. Checking Universe Coverage ---")
    c_path = os.path.join(STORE_DIR, 'companies.json')
    try:
         with open(c_path, 'r') as f:
            data = json.load(f)
         
         total = len(data)
         tech = len([c for c in data if c.get('sector') in ['Tech', 'Technology']])
         fintech = len([c for c in data if c.get('sub_industry') == 'FinTech'])
         
         print(f"  Total Companies: {total}")
         print(f"  Tech Sector: {tech}")
         print(f"  FinTech Sub-Industry: {fintech}")
         
         # Check Specific "Important" Missing?
         # User didn't specify beyond "important".
         # Let's check top 10 by mcap if I could (don't have mcap here easily)
         
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    check_radar_cache()
    check_fundamentals_store()
    check_yf_cache()
    check_universe_coverage()
