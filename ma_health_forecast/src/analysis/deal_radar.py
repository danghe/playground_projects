import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time
import concurrent.futures

class SECMonitor:
    """
    Monitors SEC EDGAR.
    """
    BASE_URL = "https://data.sec.gov/submissions/"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    
    HEADERS = {
        "User-Agent": "MAForecastProject admin@maforecast.com",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

    def __init__(self):
        self.cik_map = self._fetch_cik_map()

    def _fetch_cik_map(self):
        try:
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

    def get_cik(self, ticker):
        return self.cik_map.get(ticker.upper())

    def fetch_filings(self, ticker):
        """
        Fetches raw filings list for CatalystEngine to parse.
        """
        cik = self.get_cik(ticker)
        if not cik: return []

        url = f"{self.BASE_URL}CIK{cik}.json"
        try:
            # rate limit handled by caller or simple sleep
            time.sleep(0.1) 
            response = requests.get(url, headers=self.HEADERS)
            response.raise_for_status()
            data = response.json()
            return data.get('filings', {}).get('recent', {})
        except Exception as e:
            print(f"Error SEC {ticker}: {e}")
            return {}


class CatalystEngine:
    """
    Parses signals into a 'Catalyst Feed' of Deal Triggers.
    """
    def parse_sec_events(self, ticker, filings):
        if not filings: return []
        
        events = []
        forms = filings.get('form', [])
        dates = filings.get('filingDate', [])
        items = filings.get('items', [])
        # accession = filings.get('accessionNumber', []) # Can construct link with this
        if len(items) != len(forms): items = [""] * len(forms)

        relevant = ["SC 13D", "SC 13G", "8-K"]
        one_year_ago = datetime.now() - timedelta(days=365)

        for form, date_str, item_list in zip(forms, dates, items):
            try:
                f_date = datetime.strptime(date_str, "%Y-%m-%d")
            except: continue
            
            if f_date < one_year_ago: continue

            if form in relevant:
                event_type = None
                implication = None
                badge = "info"
                
                if form == "SC 13D":
                    event_type = "⚔️ Activist Stake"
                    implication = "Strategic Review / Divestiture likely within 6-12m"
                    badge = "danger"
                elif form == "SC 13G":
                    event_type = "Passive Stake"
                    implication = "Accumulation by Institutional Investors"
                    badge = "warning"
                elif form == "8-K":
                    if "1.01" in item_list:
                        event_type = "🤝 Material Agreement"
                        implication = "Potential JV or Commercial Trigger"
                        badge = "primary"
                    elif "1.03" in item_list:
                        event_type = "🔥 Bankruptcy/Restructuring"
                        implication = "Distressed Asset Sale Imminent"
                        badge = "danger"
                    elif "2.01" in item_list:
                         event_type = "🤝 Acquisition/Disposition"
                         implication = "Deal Closing"
                         badge = "success"
                    elif "5.02" in item_list:
                        event_type = "👋 Mgmt Departure"
                        implication = "Governance Instability / New Strategy"
                        badge = "warning"
                    elif "8.01" in item_list:
                         # Very generic, usually need text parsing. Assume generic for now unless we had text.
                         pass
                
                if event_type:
                    events.append({
                        "ticker": ticker,
                        "date": date_str,
                        "type": event_type,
                        "implication": implication,
                        "badge": badge,
                        "source": "SEC"
                    })
        return events

    def parse_market_events(self, ticker, info):
        events = []
        # 1. Price Crash
        try:
            # yfinance info sometimes has '52WeekChange' or we can look at current vs high
            price = info.get('currentPrice', 0)
            high = info.get('fiftyTwoWeekHigh', 0)
            if high > 0 and price > 0:
                drop = (high - price) / high
                if drop > 0.40: # 40% drop
                     events.append({
                        "ticker": ticker,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "📉 Deep Discount",
                        "implication": "Vulnerable to Lowball Takeover",
                        "badge": "danger",
                        "source": "Market"
                    })
        except: pass
        
        # 2. Analyst Actions
        rec = info.get('recommendationKey', '').lower()
        if rec in ['sell', 'underperform']:
             events.append({
                "ticker": ticker,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "Analyst Downgrade",
                "implication": "Sentiment Shift / Repricing",
                "badge": "warning",
                "source": "Analyst"
            })
            
        return events


class MarketScanner:
    """
    Calculates Seller Pressure Index (SPI) and Buyer Readiness.
    """
    def get_market_analysis(self, sector_tickers):
        buyers = []
        sellers = []
        
        for ticker in sector_tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # --- Basic Financials ---
                name = info.get('longName', ticker)
                price = info.get('currentPrice', info.get('previousClose', 0.0))
                market_cap = info.get('marketCap', 0.0)
                
                total_cash = info.get('totalCash', 0.0)
                total_debt = info.get('totalDebt', 0.0)
                ebitda = info.get('ebitda', 0.0)
                
                rev_growth = info.get('revenueGrowth', 0.0) 
                quick_ratio = info.get('quickRatio', 1.0)
                fifty_two_high = info.get('fiftyTwoWeekHigh', price)
                
                # --- Derived Metrics ---
                net_debt = total_debt - total_cash
                if ebitda > 0:
                    lev_ratio = net_debt / ebitda
                else:
                    lev_ratio = 99.0 if net_debt > 0 else 0.0
                    
                firepower = total_cash + (2.5 * ebitda) - total_debt
                if firepower < 0: firepower = 0.0
                
                pct_of_high = 1.0
                if fifty_two_high > 0:
                    pct_of_high = price / fifty_two_high
                    
                # --- SELLER PRESSURE INDEX (SPI) ---
                spi_score = 0
                drivers = []
                
                if lev_ratio > 4.5:
                    spi_score += 40
                    drivers.append("Solvency (Debt Wall)")
                elif lev_ratio > 3.0:
                    spi_score += 20
                    drivers.append("Elevated Leverage")
                    
                if rev_growth < -0.05:
                    spi_score += 30
                    drivers.append("Rev. Contraction")
                elif rev_growth < 0.02:
                    spi_score += 10
                    drivers.append("Growth Stall")
                    
                if pct_of_high < 0.70:
                    spi_score += 20
                    drivers.append("Valuation Dislocation")
                    
                if quick_ratio < 0.8:
                    spi_score += 10
                    drivers.append("Liquidity Tightness")
                
                pitch_thesis = "Stable Performance"
                if drivers:
                    pitch_thesis = f"Primary Driver: {drivers[0]}"
                
                seller_role = "🛡️ Stable"
                badge_bg = "secondary"
                
                if spi_score >= 75:
                    seller_role = "🔥 Forced Seller"
                    badge_bg = "danger"
                elif spi_score >= 50:
                    seller_role = "📉 Strategic Review"
                    badge_bg = "warning"
                elif spi_score >= 30:
                     seller_role = "👀 Watchlist"
                     badge_bg = "info"
                     
                
                # --- BUYER READINESS ---
                buyer_role = "Neutral"
                buyer_badge = "secondary"
                is_buyer = False
                
                if total_cash > 2_000_000_000 and lev_ratio < 2.0:
                    buyer_role = "🟢 Prime Acquirer"
                    buyer_badge = "success"
                    is_buyer = True
                elif rev_growth < 0.02 and total_cash > 500_000_000:
                    buyer_role = "🟡 Desperate Buyer"
                    buyer_badge = "warning"
                    is_buyer = True
                elif lev_ratio > 4.0:
                    buyer_role = "🔴 Constrained"
                    buyer_badge = "danger"
                
                company_data = {
                    "Ticker": ticker,
                    "Company Name": name,
                    "Price": price,
                    "Market Cap": market_cap,
                    "Firepower": firepower,
                    "Cash": total_cash,
                    "Leverage Ratio": lev_ratio,
                    "EV/EBITDA": info.get('enterpriseToEbitda', 0.0),
                    "FCF Yield": (info.get('freeCashflow', 0) / market_cap) if market_cap else 0,
                    "SPI Score": spi_score,
                    "Seller Role": seller_role,
                    "Seller Badge": badge_bg,
                    "Pitch Thesis": pitch_thesis,
                    "Buyer Role": buyer_role,
                    "Buyer Badge": buyer_badge,
                    "Is Buyer": is_buyer,
                    "Info": info # Pass info for CatalystEngine to use without refetching?
                }
                
                if is_buyer: buyers.append(company_data)
                sellers.append(company_data)

            except Exception as e:
                print(f"Error yfinance {ticker}: {e}")
                
        return buyers, sellers


def scan_market_sector(sector_name):
    SECTOR_MAP = {
        "Tech": ["AAPL", "MSFT", "NVDA", "ORCL", "CRM", "INTC", "CSCO", "PYPL", "ZOOM", "DOCU"],
        "Energy": ["XOM", "CVX", "SLB", "OXY", "KMI", "WMB", "APA", "HAL"],
        "Healthcare": ["JNJ", "PFE", "LLY", "CVS", "WBA", "DOCS", "TDOC", "MRNA"]
    }
    
    tickers = SECTOR_MAP.get(sector_name)
    if not tickers: return [], [], []

    print(f"--- Deal Origination Scan: {sector_name} ---")
    
    # 1. Financial Analysis
    scanner = MarketScanner()
    buyers, sellers = scanner.get_market_analysis(tickers)
    
    # 2. Catalyst Engine (Threaded for SEC speed?)
    catalyst_engine = CatalystEngine()
    sec_monitor = SECMonitor()
    
    catalyst_feed = []
    
    # Map back to find info for market events
    # We can use the sellers list which contains all tickers
    
    for company in sellers:
        t = company['Ticker']
        
        # A. SEC Events
        filings = sec_monitor.fetch_filings(t)
        sec_events = catalyst_engine.parse_sec_events(t, filings)
        catalyst_feed.extend(sec_events)
        
        # B. Market Events
        # We passed 'Info' in company_data to avoid refetching
        market_events = catalyst_engine.parse_market_events(t, company.get('Info', {}))
        catalyst_feed.extend(market_events)

        # Update company record with most recent 13D for display in table if wanted
        # (Optional: keep simple text summary in table)
        activist_events = [e for e in sec_events if "Activist" in e['type']]
        if activist_events:
            company['Recent Filings'] = "ACTIVIST ATTACK"
            company['SEC Alert'] = True
            # Boost SPI
            company['SPI Score'] = max(company['SPI Score'], 85)
            company['Seller Role'] = "🦈 Activist Target"
            company['Seller Badge'] = "danger"
            company['Pitch Thesis'] = "Primary Driver: Activist Pressure"
        else:
             company['Recent Filings'] = ""
             company['SEC Alert'] = False

    # 3. Sort Feed
    # Date strings are YYYY-MM-DD, so string sort works reverse
    catalyst_feed.sort(key=lambda x: x['date'], reverse=True)
    
    # 4. Sorting Lists
    buyers.sort(key=lambda x: x['Firepower'], reverse=True)
    sellers.sort(key=lambda x: x['SPI Score'], reverse=True)
    
    return buyers, sellers, catalyst_feed

if __name__ == "__main__":
    b, s, feed = scan_market_sector("Tech")
    print("FEED:")
    for f in feed[:5]:
        print(f)
