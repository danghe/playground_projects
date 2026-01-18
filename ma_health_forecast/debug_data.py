import json
import os

STORE_DIR = r"d:\00Intralinks\M&A Forecast Project\ma_health_forecast_project\ma_health_forecast\src\data\store"
UNIVERSE_FILE = os.path.join(STORE_DIR, 'companies.json')
FUNDAMENTALS_FILE = os.path.join(STORE_DIR, 'fundamentals.json')

def check_ssnc():
    print("--- Checking SSNC Data ---")
    with open(UNIVERSE_FILE, 'r') as f:
        universe = json.load(f)
    
    ssnc_meta = next((c for c in universe if c['ticker'] == 'SSNC'), None)
    if not ssnc_meta:
        print("SSNC NOT FOUND in Universe!")
        return

    print("SSNC Metadata:", json.dumps(ssnc_meta, indent=2))

    with open(FUNDAMENTALS_FILE, 'r') as f:
        funds = json.load(f)
    
    ssnc_fund = funds.get('SSNC')
    if not ssnc_fund:
        print("SSNC NOT FOUND in Fundamentals!")
    else:
        # Print key keys
        print("SSNC Fundamentals Keys:", list(ssnc_fund.keys()))
        print("SSNC Market Cap:", ssnc_fund.get('market_cap'))
        print("SSNC EBITDA:", ssnc_fund.get('ebitda'))
        print("SSNC Revenue:", ssnc_fund.get('revenue'))

def check_tech_giants():
    print("\n--- Checking Tech Giants ---")
    giants = ['CRM', 'ADBE', 'ORCL', 'SAP', 'INTC', 'AMD', 'QCOM', 'TXN', 'NOW', 'UBER', 'ABNB']
    with open(UNIVERSE_FILE, 'r') as f:
        universe = json.load(f)
    
    found = {c['ticker'] for c in universe}
    for g in giants:
        status = "FOUND" if g in found else "MISSING"
        print(f"{g}: {status}")

if __name__ == "__main__":
    check_ssnc()
    check_tech_giants()
