import requests
import time
import json

class SECClient:
    """
    Shared SEC Client for Audit-Grade Fetches.
    Handles Rate Limiting, User-Agent, and CIK Mapping.
    """
    BASE_URL = "https://data.sec.gov/submissions/"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    
    HEADERS = {
        "User-Agent": "M&A-Health-Forecast/2.0 (admin@maforecast.com)",
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }

    def __init__(self):
        self.cik_map = {}
        self.ticker_map = {}
        self._refresh_cik_map()

    def _refresh_cik_map(self):
        try:
            # print("Refreshing SEC CIK Map...")
            time.sleep(0.1)
            headers = self.HEADERS.copy()
            response = requests.get(self.TICKERS_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for entry in data.values():
                ticker = entry['ticker'].upper()
                cik = str(entry['cik_str']).zfill(10)
                title = entry['title']
                
                self.cik_map[ticker] = cik
                self.ticker_map[cik] = {'ticker': ticker, 'title': title}
                
        except Exception as e:
            print(f"Error fetching CIK map: {e}")

    def get_cik(self, ticker):
        return self.cik_map.get(ticker.upper())

    def get_ticker(self, cik):
        return self.ticker_map.get(str(cik).zfill(10), {}).get('ticker')

    def fetch_submissions(self, cik):
        """Fetches full submission history for a CIK"""
        cik = str(cik).zfill(10)
        url = f"{self.BASE_URL}CIK{cik}.json"
        
        try:
            # Rate limit mitigation (SEC allows ~10/sec)
            time.sleep(0.15) 
            headers = self.HEADERS.copy()
            headers["Host"] = "data.sec.gov"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 404: return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching submissions for {cik}: {e}")
            return None
