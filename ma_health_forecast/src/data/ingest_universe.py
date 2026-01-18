import requests
import json
import os
import yfinance as yf
import yaml
import time
import argparse
import concurrent.futures
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TAXONOMY_FILE = os.path.join(BASE_DIR, 'config', 'taxonomy.yaml')
STORE_DIR = os.path.join(os.path.dirname(__file__), 'store')

# Target Sectors to build robust universe for (Scale: 200+ total)
TARGET_SECTORS = ['Technology', 'Healthcare', 'Financial Services', 'Energy', 'Industrials'] # Broaden search
TARGET_EXCHANGES = ['NASDAQ', 'NYSE']

# Priority tickers that MUST be included regardless of other filters
# These represent major companies of strategic importance
PRIORITY_TICKERS = [
    # Major Tech
    'NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA',
    # FinTech & Financial Data
    'SSNC',  # SS&C Technologies Holdings Inc (User Priority)
    'FIS',   # Fidelity National Information Services
    'FISV',  # Fiserv
    'ADP',   # Automatic Data Processing
    'PAYX',  # Paychex
    'SQ',    # Block (Square)
    'PYPL',  # PayPal
    'V',     # Visa
    'MA',    # Mastercard
    'INTU',  # Intuit
    # Semiconductors  
    'AMD', 'INTC', 'AVGO', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC',
    # Enterprise Software
    'CRM', 'ORCL', 'SAP', 'NOW', 'ADBE', 'WDAY', 'SNOW', 'DDOG', 'ZS',
    # Electronic Gaming
    'EA',    # Electronic Arts
    'TTWO',  # Take-Two Interactive
    'RBLX',  # Roblox
    'U',     # Unity Software
    'SONY',  # Sony Group
    'APP',   # AppLovin (Mobile Gaming/AdTech)
]

# SEC Setup
SEC_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
HEADERS = {
    "User-Agent": "Intralinks Analysis tool/2.0 (admin@maforecast.com)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def ensure_store():
    if not os.path.exists(STORE_DIR):
        os.makedirs(STORE_DIR)

def load_taxonomy():
    if not os.path.exists(TAXONOMY_FILE):
        print(f"Warning: Taxonomy file not found at {TAXONOMY_FILE}")
        return {}
    with open(TAXONOMY_FILE, 'r') as f:
        return yaml.safe_load(f)

def fetch_sec_tickers():
    print(f"Fetching SEC Master List...")
    try:
        resp = requests.get(SEC_URL, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        keys = data['fields']
        rows = data['data']
        # Convert to list of dicts
        return [dict(zip(keys, r)) for r in rows]
    except Exception as e:
        print(f"Error fetching SEC data: {e}")
        return []

def classify_sub_industry(info, taxonomy):
    """
    Robust classifier using Config-Driven Taxonomy (SIC + Keywords).
    Returns: (Sector, Sub-Industry, Confidence, Method)
    Confidence: High (SIC), Medium (Keyword), Low (Fallback)
    """
    sector = info.get('sector', 'Unknown')
    industry = info.get('industry', 'Unknown')
    summary = info.get('longBusinessSummary', '').lower()
    
    # Ensure SIC is a string and handle potential missing values
    sic_raw = info.get('sic', '0')
    sic = str(sic_raw) if sic_raw else '0'
    
    # 1. Map High-Level Sector
    if sector == 'Technology': sector_bucket = 'Tech'
    elif sector == 'Healthcare': sector_bucket = 'Healthcare'
    elif sector == 'Financial Services': sector_bucket = 'Financials'
    else: sector_bucket = sector

    # 2. Tech Specific Taxonomy
    # Strict Hierarchy: SIC > Keyword (Industry) > Keyword (Summary)
    
    if sector_bucket == 'Tech' and taxonomy and 'sub_sectors' in taxonomy:
        priority_order = taxonomy.get('priority', [])
        rules = taxonomy.get('sub_sectors', {})

        # --- LEVEL 1: SIC Code (High Confidence) ---
        for sub_name in priority_order:
            if sub_name not in rules: continue
            rule = rules[sub_name]
            target_sics = [str(s) for s in rule.get('sic', []) or []]
            
            if sic in target_sics:
                return 'Technology', sub_name, 'High', f'SIC-{sic}'

        # --- LEVEL 2: Keywords (Medium Confidence) ---
        for sub_name in priority_order:
            if sub_name not in rules: continue
            rule = rules[sub_name]
            target_kws = rule.get('keywords', [])
            
            # Check Industry String
            for kw in target_kws:
                if kw.lower() in industry.lower():
                     return 'Technology', sub_name, 'Medium', f'Kw-Ind-{kw}'
            
            # Check Summary Text
            for kw in target_kws:
                 if f" {kw.lower()} " in summary or f"{kw.lower()} " in summary:
                     return 'Technology', sub_name, 'Medium', f'Kw-Sum-{kw}'
                     
        # --- LEVEL 3: Fallback (Low Confidence) ---
        # If no strict match, default to 'Software' but flag it
        return 'Technology', 'Software', 'Low', 'Fallback-Default'

    # 3. Non-Tech Taxonomy (If defined in future, currently pass-through)
    return sector_bucket, industry, 'N/A', 'Sector-Default'

def calculate_valuation_metrics(info):
    """
    Computes EV/EBITDA with fallbacks to EV/OpInc or P/E.
    Returns: (val_value, val_label, val_method)
    """
    try:
        mkt_cap = info.get('marketCap', 0.0) or 0.0
        ev = info.get('enterpriseValue', 0.0) or 0.0
        ebitda = info.get('ebitda', 0.0) or 0.0
        op_inc = info.get('operatingIncome', 0.0) or 0.0
        pe = info.get('trailingPE', 0.0) or 0.0
        
        # Fallback EV calc
        if ev == 0.0 and mkt_cap > 0:
             # Basic EV = MktCap + Debt - Cash
             total_cash = info.get('totalCash', 0.0) or 0.0
             total_debt = info.get('totalDebt', 0.0) or 0.0
             ev = mkt_cap + total_debt - total_cash

        # 1. EV/EBITDA
        if ev > 0 and ebitda > 0:
            val = ev / ebitda
            if 2.0 < val < 100.0: # Sanity check
                return val, f"{val:.1f}x", "EV/EBITDA"
                
        # 2. EV/EBIT (OpInc)
        if ev > 0 and op_inc > 0:
            val = ev / op_inc
            if 2.0 < val < 100.0:
                return val, f"{val:.1f}x", "EV/EBIT"
        
        # 3. P/E
        if pe > 0:
             if 5.0 < pe < 200.0:
                 return pe, f"{pe:.1f}x", "P/E"
                 
        return None, "N/A", "Missing Data"
        
    except:
        return None, "N/A", "Error"

def _fetch_single_ticker(t, max_retries=3):
    """Helper for parallel fetching with retry logic"""
    import random
    
    for attempt in range(max_retries):
        try:
            # Add jitter to avoid thundering herd
            if attempt > 0:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            
            stock = yf.Ticker(t)
            info = stock.info
            
            # Must have basic info
            if not info or info.get('regularMarketPrice') is None:
                if attempt < max_retries - 1:
                    continue  # Retry
                return t, None

            # Extract Raw Fundamentals
            market_cap = info.get('marketCap', 0.0) or 0.0
            
            # --- VALUATION COMPUTATION ---
            val_val, val_lbl, val_method = calculate_valuation_metrics(info)
            
            data = {
                # Core Identifiers
                "sector": info.get('sector', 'Unknown'),
                "industry": info.get('industry', 'Unknown'),
                "sic": str(info.get('sic', '')),
                "longBusinessSummary": info.get('longBusinessSummary', ''),
                
                # Company Names (for display)
                "short_name": info.get('shortName', ''),
                "long_name": info.get('longName', ''),
                
                # Raw Financials (Stored for Firepower/Logic)
                "market_cap": market_cap,
                "total_cash": info.get('totalCash', 0.0) or 0.0,
                "total_debt": info.get('totalDebt', 0.0) or 0.0,
                "ebitda": info.get('ebitda', 0.0) or 0.0,
                "operating_income": info.get('operatingIncome', 0.0) or 0.0,
                "total_revenue": info.get('totalRevenue', 0.0) or 0.0,
                "free_cashflow": info.get('freeCashflow', 0.0) or 0.0,
                "enterprise_value": info.get('enterpriseValue', 0.0) or 0.0,
                "previous_close": info.get('previousClose', 0.0),
                "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 0.0),
                "revenue_growth": info.get('revenueGrowth', 0.0),
                "quick_ratio": info.get('quickRatio', 0.0),
                
                # Volume/Liquidity (for relevance ranking)
                "average_volume": info.get('averageVolume', 0) or 0,
                "average_volume_10d": info.get('averageVolume10days', 0) or 0,
                
                # Computed Valuation (Persisted for speed)
                "valuation_score": val_val,   # Numeric (for sorting)
                "valuation_label": val_lbl,   # String "12.5x"
                "valuation_method": val_method, # String "EV/EBITDA"
                
                # Metadata
                "currency": info.get('currency', 'USD'),
                "provenance": {
                    "source": "yfinance",
                    "timestamp": datetime.now().isoformat()
                }
            }
            return t, data
        except Exception as e:
            if attempt < max_retries - 1:
                continue  # Retry on exception
            return t, None
    
    return t, None

def fetch_financials_batch(tickers):
    """
    Robust Fundamentals Fetcher (Parallelized).
    Captures thorough balance sheet/income data for Firepower & Valuation.
    """
    results = {}
    print(f"  > Fetching financials for {len(tickers)} companies (Parallel)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Map futures to tickers
        future_to_ticker = {executor.submit(_fetch_single_ticker, t): t for t in tickers}
        
        completed = 0
        total = len(tickers)
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            t, data = future.result()
            if data:
                results[t] = data
            
            completed += 1
            if completed % 50 == 0:
                print(f"    ... fetched {completed}/{total}", end='\r')
                
    print(f"    Simple Done. Success rate: {len(results)}/{len(tickers)}")
    return results

def load_store():
    ensure_store()
    c_path = os.path.join(STORE_DIR, 'companies.json')
    f_path = os.path.join(STORE_DIR, 'fundamentals.json')
    
    companies = []
    fundamentals = {}
    
    if os.path.exists(c_path):
        with open(c_path, 'r') as f: companies = json.load(f)
    if os.path.exists(f_path):
        with open(f_path, 'r') as f: fundamentals = json.load(f)
        
    return companies, fundamentals

def save_store(companies, fundamentals):
    ensure_store()
    with open(os.path.join(STORE_DIR, 'companies.json'), 'w') as f:
        json.dump(companies, f, indent=2)
    with open(os.path.join(STORE_DIR, 'fundamentals.json'), 'w') as f:
        json.dump(fundamentals, f, indent=2)
        
    # Metadata for Freshness
    with open(os.path.join(STORE_DIR, 'metadata.json'), 'w') as f:
        json.dump({"last_run": datetime.now().isoformat()}, f)

def is_fresh():
    meta_path = os.path.join(STORE_DIR, 'metadata.json')
    if not os.path.exists(meta_path): return False
    try:
        with open(meta_path, 'r') as f:
            last_run = datetime.fromisoformat(json.load(f)['last_run'])
        if (datetime.now() - last_run).total_seconds() < 86400: # 24 Hours
            return True
    except:
        return False
    return False

def run_ingestion(limit=300, force=False):
    taxonomy = load_taxonomy()
    
    # 0. Freshness Check (User Requirement: "once a day")
    if not force and is_fresh():
        print("--- Ingestion Skipped (Data is Fresh < 24h) ---")
        return

    # 1. Master List
    sec_data = fetch_sec_tickers()
    candidates = [c for c in sec_data if c.get('exchange') in TARGET_EXCHANGES]
    print(f"Candidates (NYSE/NASDAQ): {len(candidates)}")
    
    # 2. Resumable State
    universe, fundamentals_store = load_store()
    existing_tickers = set([c['ticker'] for c in universe])
    
    count = len(universe)
    print(f"Resuming with {count} existing companies...")
    
    # 2.5 Process Priority Tickers FIRST (Must-Have Companies)
    priority_missing = [t for t in PRIORITY_TICKERS if t not in existing_tickers]
    if priority_missing:
        print(f"Processing {len(priority_missing)} priority tickers: {priority_missing[:10]}...")
        
        # Create synthetic candidate entries for priority tickers
        sec_ticker_map = {c['ticker']: c for c in sec_data}
        priority_chunk = []
        for t in priority_missing:
            if t in sec_ticker_map:
                priority_chunk.append(sec_ticker_map[t])
            else:
                # Create minimal entry for tickers not in SEC list
                priority_chunk.append({'ticker': t, 'name': t, 'cik': 0, 'exchange': 'NASDAQ'})
        
        # Fetch financials for priority tickers
        priority_fin = fetch_financials_batch(priority_missing)
        
        for t in priority_missing:
            if t not in priority_fin: 
                print(f"  Warning: Could not fetch {t}")
                continue
            
            data = priority_fin[t]
            # Skip market cap filter for priority tickers
            sector, sub_ind, conf, method = classify_sub_industry(data, taxonomy)
            
            # Get SEC info if available
            sec_info = sec_ticker_map.get(t, {'name': data.get('short_name', t), 'cik': 0, 'exchange': 'NASDAQ'})
            
            company_entry = {
                "ticker": t,
                "title": sec_info.get('name', data.get('short_name', t)),
                "short_name": data.get('short_name', ''),
                "long_name": data.get('long_name', ''),
                "cik": str(sec_info.get('cik', 0)).zfill(10),
                "exchange": sec_info.get('exchange', 'NASDAQ'),
                "sector": sector,
                "sub_industry": sub_ind,
                "classification_confidence": conf,
                "classification_method": method,
                "market_cap": data['market_cap'],
                "average_volume": data.get('average_volume', 0),
                "priority": True  # Mark as priority company
            }
            universe.append(company_entry)
            fundamentals_store[t] = data
            existing_tickers.add(t)
            count += 1
            print(f"  ✓ Added priority: {t} ({sector}/{sub_ind})")
        
        # Save after priority processing
        save_store(universe, fundamentals_store)
        print(f"Priority tickers processed. Universe now: {count}")
    
    # 3. Processing (Regular candidates)
    chunk_size = 25  # Reduced from 100 to avoid rate limits
    
    # Filter candidates to prioritize Target Sectors before general limit
    # We want to ensure we get ALL Tech companies possible within the limit
    
    # Sort candidates: 
    # 1. Tech Sector (if known from SEC or prev run) -> Priority
    # 2. Market Cap (if known)
    # 3. Random
    
    candidates = [c for c in candidates if c['ticker'] not in existing_tickers]
    
    # Fetch batch to find sector matches? No, too expensive.
    # Just rely on limit increase to 4000 to capture everything relevant.
    
    tech_count = 0 
    
    for i in range(0, min(len(candidates), limit), chunk_size):
        if count >= limit: break
        
        chunk = candidates[i:i+chunk_size]
        tickers = [c['ticker'] for c in chunk]
        
        # Fetch Financials with delay between batches
        fin_data = fetch_financials_batch(tickers)
        
        # Add delay between batches to avoid rate limiting
        time.sleep(2)
        
        chunk_companies = []
        for t in tickers:
            if t not in fin_data: continue
            
            data = fin_data[t]
            
            # Must have minimal data (Market Cap)
            # LOWER THRESHOLD for Tech to ensure breadth (200M vs 500M)
            min_mcap = 200_000_000 # $200M
            if data['market_cap'] < min_mcap:
                continue
                
            # Classify
            sector, sub_ind, conf, method = classify_sub_industry(data, taxonomy)
            
            # Anti-Collapse: Track Tech Count
            if sector == 'Technology' or sector == 'Tech':
                tech_count += 1
            
            # Save to Universe List (Metadata)
            company_entry = {
                "ticker": t,
                "title": [c['name'] for c in chunk if c['ticker'] == t][0],
                "short_name": data.get('short_name', ''),
                "long_name": data.get('long_name', ''),
                "cik": str([c['cik'] for c in chunk if c['ticker'] == t][0]).zfill(10),
                "exchange": [c['exchange'] for c in chunk if c['ticker'] == t][0],
                "sector": sector,
                "sub_industry": sub_ind,
                "classification_confidence": conf,
                "classification_method": method,
                "market_cap": data['market_cap'],
                "average_volume": data.get('average_volume', 0),
                "relevance_score": 0 # TODO: Calc relevance
            }
            chunk_companies.append(company_entry)
            fundamentals_store[t] = data
            count += 1
            
        # Incremental Save
        universe.extend(chunk_companies)
        save_store(universe, fundamentals_store)
        print(f"  [Progress] Ingested {count} companies. Tech Count in Session: {tech_count}")

    print(f"\n--- Ingestion Complete ---")
    print(f"Total Companies: {len(universe)}")
    print(f" Outputs: {STORE_DIR}/companies.json, fundamentals.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=8000, help='Target universe size')
    parser.add_argument('--force', action='store_true', help='Force re-ingestion')
    args = parser.parse_args()
    
    run_ingestion(limit=args.limit, force=args.force)
