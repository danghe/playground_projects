import requests
import json
import os
import yfinance as yf
import concurrent.futures
from datetime import datetime, timedelta
from src.data.providers.yfinance_provider import YFinanceProvider
from src.data.universe_service import UniverseService
from src.analysis.spi_engine import SPIEngine
from src.analysis.trend_engine import IndustryTrendEngine
from src.analysis.playbook_engine import PlaybookEngine
import time
import math

class StrategicSECMonitor:
    """
    Audit-Grade SEC Monitor.
    - Truth Source: data.sec.gov
    - Capabilities: Form 4 Cluster detection, Provenance linking.
    """
    BASE_URL = "https://data.sec.gov/submissions/"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    
    # Audit requirement: Valid User-Agent
    HEADERS = {
        "User-Agent": "M&A-Health-Forecast/1.0 (admin@maforecast.com)",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

    def __init__(self):
        self.cik_map = self._fetch_cik_map()

    def _fetch_cik_map(self):
        try:
            # Respect SEC rate limits
            time.sleep(0.1)
            headers = self.HEADERS.copy()
            headers["Host"] = "www.sec.gov"
            response = requests.get(self.TICKERS_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            cik_map = {}
            for entry in data.values():
                ticker = entry['ticker'].upper()
                cik = entry['cik_str']
                cik_padded = str(cik).zfill(10)
                cik_map[ticker] = cik_padded
            return cik_map
        except Exception as e:
            print(f"Error fetching CIK map: {e}")
            return {}

    def fetch_filing_history(self, ticker):
        cik = self.cik_map.get(ticker.upper())
        if not cik: return None
        
        url = f"{self.BASE_URL}CIK{cik}.json"
        try:
            time.sleep(0.12) # Rate limit padding
            response = requests.get(url, headers=self.HEADERS)
            if response.status_code == 404: return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"SEC Fetch Error {ticker}: {e}")
            return None

    def analyze_filings(self, ticker, sec_data):
        if not sec_data: return [], [], 0 # Catalysts, Evidence, GovernanceScore
        
        catalysts = []
        governance_hits = 0
        recent = sec_data.get('filings', {}).get('recent', {})
        if not recent: return [], [], 0

        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        items = recent.get('items', []) # Only for 8-K
        accessions = recent.get('accessionNumber', [])
        primary_doc = recent.get('primaryDocument', [])

        # Time Windows
        today = datetime.now()
        six_months = today - timedelta(days=180)
        
        # Deduplication Tracker (Set of (date, type))
        seen_events = set()
        
        # Lists for Form 4 Counting
        form_4_dates = []

        # Iterate filings
        length = len(forms)
        for i in range(length):
            try:
                f_date = datetime.strptime(dates[i], "%Y-%m-%d")
            except: continue
            
            # Skip old history
            if f_date < six_months: continue

            form = forms[i]
            acc_num = accessions[i] if i < len(accessions) else ""
            doc_name = primary_doc[i] if i < len(primary_doc) else ""
            
            # Construct Link for Provenance
            cik = self.cik_map.get(ticker.upper())
            link = ""
            if cik and acc_num and doc_name:
                clean_acc = acc_num.replace("-", "")
                link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{clean_acc}/{doc_name}"

            # --- Logic ---

            event_type = None
            headline = ""
            confidence = "Low"
            implication = ""
            badge = "secondary"

            # 1. Activist Stake (13D) - High Confidence
            if form == "SC 13D":
                event_type = "⚔️ Activist Stake"
                headline = "13D Filing: Aggressive Stake"
                confidence = "High"
                implication = "Strategic Review / Divestiture likely"
                badge = "danger"
                governance_hits += 1

            # 2. Material Events (8-K)
            elif form == "8-K":
                item_list = items[i] if i < len(items) else ""
                
                if "1.01" in item_list:
                    event_type = "🤝 Material Agreement"
                    headline = "Entry into Material Definitive Agreement"
                    confidence = "Medium"
                    implication = "Commercial Trigger / Partnership"
                    badge = "primary"
                
                elif "1.03" in item_list:
                    event_type = "🔥 Restructuring"
                    headline = "Bankruptcy / Receivership"
                    confidence = "High"
                    implication = "Distressed Asset Sale"
                    badge = "danger"
                    
                elif "2.01" in item_list: # Disposition / Acquisition
                    event_type = "💰 M&A Event"
                    headline = "Completion of Acquisition/Disposition"
                    confidence = "High"
                    implication = "Portfolio Reshaping"
                    badge = "primary"
                    
                elif "5.02" in item_list:
                    event_type = "👋 Mgmt Departure"
                    headline = "Departure of Directors/Officers"
                    confidence = "Medium"
                    implication = "Governance Instability"
                    badge = "warning"
                    governance_hits += 1
            
            # 3. Form 4 (Insider Buy) - Collect dates
            elif form == "4":
                # Only care if recent (30 days) for counting
                if (today - f_date).days < 30:
                    form_4_dates.append(f_date)
            
            # --- Result Construction & Dedupe ---
            if event_type:
                unique_key = (dates[i], event_type)
                if unique_key not in seen_events:
                    seen_events.add(unique_key)
                    catalysts.append({
                        "date": dates[i],
                        "type": event_type,
                        "headline": headline,
                        "confidence": confidence,
                        "implication": implication,
                        "badge": badge,
                        "link": link
                    })

        # --- Post-Loop Analysis ---
        
        # Form 4 Cluster: >3 buys in last 30 days
        if len(form_4_dates) >= 3:
            catalysts.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "🟢 Insider Cluster",
                "headline": f"Strong Insider Confidence ({len(form_4_dates)} buys)",
                "confidence": "High",
                "implication": "Insiders buying dip before news?",
                "badge": "success",
                "link": f"https://www.sec.gov/edgar/browse/?CIK={self.cik_map.get(ticker.upper())}"
            })

        return catalysts, len(form_4_dates), governance_hits


class StrategicMarketEngine:
    """
    Audit-Grade Financial Engine.
    Formulaic Firepower & SPI.
    Uses MarketDataProvider with caching.
    """
    def __init__(self):
        self.provider = YFinanceProvider()

    def analyze_ticker(self, ticker, sec_monitor, pre_fetched_fund=None):
        # 1. Fetch Audit-Grade Data (with Provenance)
        if pre_fetched_fund:
            fund = pre_fetched_fund
        else:
            fund = self.provider.get_fundamentals(ticker)
        
        # 2. Extract Key Financials (Robustly from Store)
        price = fund.get('previous_close', 0.0)
        market_cap = fund.get('market_cap', 0.0) # Might be 0.0
        
        # Sparkline
        sparkline = self.provider.get_sparkline(ticker)
        
        # Critical Financials
        cash = fund.get('total_cash', 0.0)
        debt = fund.get('total_debt', 0.0)
        ebitda = fund.get('ebitda', 0.0)
        rev_growth = fund.get('revenue_growth', 0.0)
        
        # Valuation (Pre-calculated in Ingestion)
        val_score = fund.get('valuation_score', None)
        val_label = fund.get('valuation_label', 'N/A')
        
        # Provenance Metadata
        provenance = fund.get('provenance', {})
        data_source = provenance.get('source', 'Unknown')

        # 3. SEC Analysis
        sec_raw = sec_monitor.fetch_filing_history(ticker)
        catalysts, insider_count, gov_hits = sec_monitor.analyze_filings(ticker, sec_raw)

        # --- METRIC 1: FIREPOWER (Buying Capacity) ---
        # Formula: Cash + (Leverage Capacity) - Debt
        # Target Leverage: 3.0x EBITDA
        # If EBITDA missing, Firepower = Cash - Debt (Conservative)
        # If Cash/Debt missing: fallback logic strictly handles N/A
        
        firepower = 0.0
        firepower_label = "$0.0B"
        
        try:
            leverage_capacity = 3.0 * ebitda if ebitda > 0 else 0.0
            gross_capacity = cash + leverage_capacity
            net_capacity = gross_capacity - debt
            firepower = max(0.0, net_capacity)
            firepower_label = f"${firepower/1e9:.1f}B"
            
            # If we have absolutely no data (Cap=0, Cash=0, Debt=0), flag as N/A
            if market_cap == 0 and cash == 0 and debt == 0:
                firepower_label = "N/A"
                
        except:
             firepower_label = "N/A"

        # --- METRIC 2: SELLER PRESSURE INDEX (SPI) ---
        spi_result = SPIEngine.calculate(ticker, fund, catalysts, gov_hits)
        spi_score = spi_result['total_score']
        spi_breakdown = spi_result['breakdown']
        
        # Calculate leverage ratio for buyer readiness logic
        net_debt = debt - cash
        leverage_ratio = net_debt / ebitda if ebitda > 0 else (99.0 if net_debt > 0 else 0.0)

        # --- BUYER READINESS (0-100) ---
        fp_ratio = min(firepower / market_cap, 1.0) if market_cap > 0 else 0
        readiness_score = (fp_ratio * 50) 
        if rev_growth is not None and rev_growth < 0.05: readiness_score += 30 # Growth stall
        if cash > 5e9: readiness_score += 20 
        readiness_score = min(round(readiness_score), 100)

        # --- SUSCEPTIBILITY (0-100) ---
        comps = spi_result['components']
        susceptibility = (comps['price'] * 2.5) + (comps['governance'] * 2.5)
        susceptibility = min(round(susceptibility), 100)

        # --- DEAL IMMINENCE (0-100) ---
        imminence_base = spi_score * 0.2
        catalyst_score = 0
        confidence_map = {"High": 25, "Medium": 15, "Low": 5}
        
        for cat in catalysts:
            grade = cat.get('confidence', 'Low')
            catalyst_score += confidence_map.get(grade, 5)
            
        imminence = imminence_base + catalyst_score
        imminence = min(round(imminence), 100)

        # --- PATH PREDICTION ---
        most_likely_path = "Status Quo"
        path_rationale = "No strong signals"
        
        if imminence > 60:
            if spi_score > 60:
                if comps['balance_sheet'] > 15:
                    most_likely_path = "Distressed Sale"
                elif comps['governance'] > 10:
                    most_likely_path = "Activist / Take-Private"
                else:
                    most_likely_path = "Strategic Acquisition"
            elif readiness_score > 70:
                most_likely_path = "Aggressive Consolidator"
        elif susceptibility > 70:
            most_likely_path = "Vulnerable Target"
        elif readiness_score > 60:
             most_likely_path = "Programmatic Buyer"

        # --- UNIFIED DRIVERS (Badges) ---
        top_drivers = []
        # 1. SPI Drivers
        for driver in spi_breakdown:
             top_drivers.append({"label": driver, "type": "danger", "desc": "High SPI Component", "link": None})
        
        # 2. Catalysts (Deduped)
        for cat in catalysts:
            desc_text = f"[{cat.get('confidence','M')}] {cat.get('headline', '')} -> {cat.get('implication', '')}"
            top_drivers.append({"label": cat['type'], "type": "warning", "desc": desc_text, "link": cat.get('link')})
            
        # Deduplicate Drivers (Label + Type)
        unique_drivers = []
        seen_drivers = set()
        for d in top_drivers:
            key = (d['label'], d['type'])
            if key not in seen_drivers:
                seen_drivers.add(key)
                unique_drivers.append(d)

        # --- Company Name Resolution (Robust Fallback) ---
        # Priority: pre_fetched title > short_name > long_name > ticker
        company_name = ticker
        if pre_fetched_fund:
            company_name = (
                pre_fetched_fund.get('title') or 
                pre_fetched_fund.get('short_name') or 
                pre_fetched_fund.get('long_name') or 
                ticker
            )
        else:
            company_name = (
                fund.get('short_name') or 
                fund.get('long_name') or 
                ticker
            )

        # --- UNIFIED OUTPUT OBJECT ---
        return {
            "ticker": ticker,
            "name": company_name,
            "sector": fund.get('sector', 'Unknown'),
            # Sub-Industry injected by scan_sector_audit
            
            "scores": {
                "spi": spi_score,
                "buyer_readiness": int(readiness_score),
                "susceptibility": int(susceptibility),
                "imminence": int(imminence)
            },
            
            "prediction": {
                "path": most_likely_path,
                "rationale": path_rationale
            },

            "evidence": {
                "price": price,
                "leverage_ratio": round(leverage_ratio, 2),
                "top_drivers": unique_drivers[:4],
                "firepower": firepower if isinstance(firepower, (int, float)) else 0.0,
                "val_score": val_score,
                "ev_ebitda": val_score if val_score else 0.0 # Backwards compat for template
            },
            "firepower_raw": firepower,   # Numeric for sorting
            "cash": cash,
            "ev_ebitda": val_label,       # From pre-calc
            "val_score": val_score,
            "components": comps,
            "data_source": data_source,
            "growth_rate": round((rev_growth or 0) * 100, 1),
            "spi_drivers": spi_breakdown,
            
            "catalysts": catalysts,
            "sparkline": sparkline
        }



# Valid Cache Duration: 24 Hours
RADAR_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'store', 'radar')

def ensure_radar_cache_dir():
    if not os.path.exists(RADAR_CACHE_DIR):
        os.makedirs(RADAR_CACHE_DIR)

def get_radar_cache(sector_name):
    # 1. Check File Existence
    filename = f"radar_{sector_name.lower()}.json"
    filepath = os.path.join(RADAR_CACHE_DIR, filename)
    
    if not os.path.exists(filepath):
        return None
        
    try:
        # 2. Check Freshness
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        timestamp = data.get('timestamp')
        if not timestamp: return None
        
        last_run = datetime.fromisoformat(timestamp)
        if (datetime.now() - last_run).total_seconds() < 86400: # 24 Hours
            return data['payload'] # (results, heatmap, narrative, playbook)
            
    except Exception as e:
        print(f"Cache Read Error {sector_name}: {e}")
        return None
        
    return None

def save_radar_cache(sector_name, results, heatmap, narrative, playbook):
    ensure_radar_cache_dir()
    filename = f"radar_{sector_name.lower()}.json"
    filepath = os.path.join(RADAR_CACHE_DIR, filename)
    
    payload = (results, heatmap, narrative, playbook)
    
    container = {
        "timestamp": datetime.now().isoformat(),
        "sector": sector_name,
        "payload": payload
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(container, f, indent=2)
    except Exception as e:
        print(f"Cache Write Error {sector_name}: {e}")

def scan_sector_audit_streaming(sector_name):
    """
    Streaming version of scan_sector_audit that yields progress updates.
    Yields dicts: {progress: 0-100, status: str, ticker: str, complete: bool, data: optional}
    """
    # 0. Cache Check - If cached, return immediately
    cached = get_radar_cache(sector_name)
    if cached:
        print(f"--- Loaded Cached Radar: {sector_name} ---")
        yield {
            "progress": 100,
            "status": "Loaded from cache (< 24h old)",
            "ticker": None,
            "complete": True,
            "cached": True,
            "data": cached
        }
        return

    yield {
        "progress": 0,
        "status": "Starting universe scan...",
        "ticker": None,
        "complete": False
    }
    
    print(f"--- Starting Audit-Grade Scan: {sector_name} ---")
    
    # Dynamic Universe Load
    universe = UniverseService()
    tickers = universe.get_tickers(sector=sector_name)
    sector_map = universe.get_sector_map(sector_name)
    
    # Fallback if universe is empty (e.g. not built yet)
    if not tickers:
        print("WARN: Universe empty. Falling back to default list.")
        SECTORS_DEFAULT = {
            "Tech": ["AAPL", "MSFT", "NVDA", "CRM", "ADBE", "INTC", "CSCO", "PYPL", "ZOOM", "DOCU", "AMD", "IBM", "NOW", "SNOW", "PLTR"],
        }
        tickers = SECTORS_DEFAULT.get(sector_name, SECTORS_DEFAULT["Tech"])
    
    total_tickers = len(tickers)
    yield {
        "progress": 5,
        "status": f"Found {total_tickers} companies to scan...",
        "ticker": None,
        "complete": False
    }
    
    sec = StrategicSECMonitor()
    market = StrategicMarketEngine()
    
    results = []
    
    # Helper for parallel execution
    def _analyze_target(t):
        try:
            # Use fundamentals from sector_map (includes valuation from ingestion)
            # sector_map is enriched with fundamentals in get_sector_map()
            pre_fetched = sector_map.get(t) if t in sector_map else None
            
            data = market.analyze_ticker(t, sec, pre_fetched_fund=pre_fetched)
            
            if data:
                # Inject Sub-Industry and Company Name from sector_map
                if t in sector_map:
                    data['sub_industry'] = sector_map[t].get('sub_industry', 'Other')
                    # Use title (SEC name) if name is just the ticker
                    if data.get('name') == t or not data.get('name'):
                        data['name'] = sector_map[t].get('title') or sector_map[t].get('short_name') or t
                return data
        except Exception as e:
            print(f"Skipping {t}: {e}")
        return None

    # Parallel Execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(_analyze_target, t): t for t in tickers}
        
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            completed_count += 1
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                print(f"Worker Error: {e}")

            # Yield progress (5% to 90% for scanning phase)
            progress = 5 + int(completed_count / total_tickers * 85)
            yield {
                "progress": progress,
                "status": f"Scanned {completed_count}/{total_tickers} companies",
                "ticker": future_to_ticker[future], # Show which ticker finished
                "complete": False,
                "scanned_count": len(results)
            }
            
    yield {
        "progress": 92,
        "status": "Calculating trends and heatmap...",
        "ticker": None,
        "complete": False
    }
    
    # Calculate Trends (Heatmap & Narrative)
    trends = IndustryTrendEngine.aggregate(results, sector_map)
    heatmap_data = trends['heatmap']
    narrative_points = trends['narrative']
    
    yield {
        "progress": 95,
        "status": "Generating strategy playbook...",
        "ticker": None,
        "complete": False
    }
    
    # Calculate SPI Breadth for Playbook
    high_spi_count = 0
    total_companies = len(results)
    for r in results:
        if r['scores']['spi'] > 60:
            high_spi_count += 1
            
    spi_breadth = (high_spi_count / total_companies * 100) if total_companies > 0 else 0

    # Generate Strategy Playbook
    import yfinance as yf
    vix_val = 20.0
    try:
        hist = yf.Ticker("^VIX").history(period="5d")
        if not hist.empty:
            vix_val = hist['Close'].iloc[-1]
    except:
        pass
        
    financing_state = "Closed" if vix_val > 25 else "Open"
    
    market_state_input = {
        "vix": vix_val,
        "financing_window": financing_state
    }
    sector_stats_input = {
        "spi_breadth": spi_breadth
    }
    
    playbook = PlaybookEngine.generate_playbook(market_state_input, sector_stats_input)

    # Sort by SPI descending by default (find deals)
    results.sort(key=lambda x: x['scores']['spi'], reverse=True)
    
    yield {
        "progress": 98,
        "status": "Saving to cache...",
        "ticker": None,
        "complete": False
    }
    
    # Save Cache
    save_radar_cache(sector_name, results, heatmap_data, narrative_points, playbook)
    
    # Final yield with complete data
    yield {
        "progress": 100,
        "status": "Complete",
        "ticker": None,
        "complete": True,
        "cached": False,
        "data": (results, heatmap_data, narrative_points, playbook)
    }


def scan_sector_audit(sector_name):
    """
    Original synchronous function - now wraps streaming version.
    """
    # Consume the generator and return final result
    result = None
    for progress in scan_sector_audit_streaming(sector_name):
        if progress.get('complete'):
            result = progress.get('data')
    return result

if __name__ == "__main__":
    # Test Run
    data, heatmap, narrative, playbook = scan_sector_audit("Tech")
    print(f"\n--- TRENDS ---")
    for n in narrative: print(n)
    
    for d in data[:3]:
        print(f"\n{d['ticker']} | SPI: {d['scores']['spi']} | Drivers: {d['evidence'].get('top_drivers', 'N/A')}")
        print(f"Firepower: ${d['evidence']['firepower']/1e9:.1f}B")
        if d['catalysts']:
            print(f"Catalysts: {[c['type'] for c in d['catalysts']]}")
