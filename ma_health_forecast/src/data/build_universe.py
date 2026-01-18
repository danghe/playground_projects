import requests
import json
import os
import yfinance as yf
import yaml
import time
import argparse

# Config
SEC_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
TAXONOMY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'taxonomy.yaml')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'universe.json')

HEADERS = {
    "User-Agent": "Intralinks Analysis tool/1.0 (admin@maforecast.com)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def load_taxonomy():
    if not os.path.exists(TAXONOMY_FILE):
        return {}
    with open(TAXONOMY_FILE, 'r') as f:
        return yaml.safe_load(f)

def fetch_sec_tickers():
    print(f"Fetching SEC tickers from {SEC_URL}...")
    try:
        resp = requests.get(SEC_URL, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        
        # Format: {"data": [[cik, name, ticker, exchange], ...], "fields": [...]}
        fields = data['fields']
        rows = data['data']
        
        companies = []
        for r in rows:
            entry = dict(zip(fields, r))
            companies.append(entry)
            
        return companies
    except Exception as e:
        print(f"Error fetching SEC data: {e}")
        return []

def apply_taxonomy(info, taxonomy):
    """
    Map yfinance sector/industry/summary to our taxonomy.
    """
    sector = info.get('sector', 'Unknown')
    industry = info.get('industry', 'Unknown')
    summary = info.get('longBusinessSummary', '').lower()
    
    # Default
    if sector != 'Technology':
        return sector, "Other"
        
    mapped_sub = "Software" # Default for Tech if undefined
    
    # Check Taxonomy Rules for Tech
    tech_rules = taxonomy.get('sectors', {}).get('Tech', {}).get('sub_industries', {})
    
    found = False
    for sub, rules in tech_rules.items():
        for kw in rules.get('keywords', []):
            if kw in industry.lower() or kw in summary:
                mapped_sub = sub
                found = True
                break
        if found: break
    
    return "Tech", mapped_sub

def build_universe(limit=None):
    print("--- Building Universe ---")
    taxonomy = load_taxonomy()
    
    # 1. Fetch Source of Truth
    sec_data = fetch_sec_tickers()
    print(f"Total SEC entries: {len(sec_data)}")
    
    # 2. Filter (Nasdaq/NYSE)
    # Exchanges: Nasdaq=NASDAQ, NYSE=NYSE
    target_exchanges = ['NASDAQ', 'NYSE']
    filtered = [c for c in sec_data if c.get('exchange') in target_exchanges]
    print(f"Filtered for Major Exchanges: {len(filtered)}")
    
    # Sort by CIK or something stable? Let's process.
    universe = []
    
    count = 0
    # Process Loop
    for c in filtered:
        if limit and count >= limit:
            break
            
        ticker = c['ticker']
        cik = c['cik']
        name = c['name']
        
        # Skip weird tickers
        if len(ticker) > 5: continue
        
        try:
            # Enrichment
            # We need to filter for Tech mostly, but we don't know sector until we fetch.
            # To be efficient, let's fetch batch or one by one? 
            # yfinance is slow one by one. But for this task let's do one by one for reliability first.
            # Optimization: Check if we have a cache? (Skipping for now).
            
            # Let's try to identify potential tech by name? No, dangerous.
            # Just fetch.
            
            stock = yf.Ticker(ticker)
            # Use fast info if possible, referencing 'sector' directly might be slow
            # info = stock.info # This is the slow part.
            
            # Optimization: Using 'fast_info' doesn't give sector. Must use .info
            # We will rely on the limit to keep runtime reasonable for User request (200 acceptance criteria).
            
            info = stock.info
            
            # Check eligibility (Market Cap > 2B for "Real" Universe?)
            mcap = info.get('marketCap', 0)
            if mcap and mcap < 500_000_000: # Skip microcaps
                continue
                
            yf_sector = info.get('sector', 'Unknown')
            
            # We mainly want Tech for the prompt requirements "trends within TECH"
            # But let's keep all huge companies?
            # User Criteria: "Selecting TECH shows at least 200 companies"
            
            mapped_sector, mapped_sub = apply_taxonomy(info, taxonomy)
            
            # Filter: If we only want to build a Tech universe or a full one?
            # Instructions say "Convert watchlist into a real universe".
            # Let's keep it if it is Tech or large cap.
            
            if mapped_sector == 'Tech' or mcap > 10_000_000_000:
                print(f"[{count+1}] Added {ticker}: {mapped_sector} > {mapped_sub} (${mcap/1e9:.1f}B)")
                
                universe.append({
                    "ticker": ticker,
                    "title": name,
                    "cik": str(cik).zfill(10),
                    "exchange": c['exchange'],
                    "sector": mapped_sector,
                    "sub_industry": mapped_sub,
                    "market_cap": mcap,
                    "country": info.get('country', 'Unknown'),
                    "sic": info.get('sic', '') # SIC Code
                })
                count += 1
                
        except Exception as e:
            # print(f"Failed {ticker}: {e}")
            pass
            
    # 3. Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(universe, f, indent=2)
        
    print(f"--- Universe Built: {len(universe)} companies saved to {OUTPUT_FILE} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=250, help='Limit stored companies')
    args = parser.parse_args()
    
    build_universe(limit=args.limit)
