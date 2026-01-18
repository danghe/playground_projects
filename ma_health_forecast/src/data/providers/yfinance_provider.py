import yfinance as yf
import json
import os
import time
from datetime import datetime
from src.data.market_data import MarketDataProvider
from typing import Dict, List, Any

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
FUNDAMENTALS_TTL = 3600 * 12 # 12 Hours
PRICE_TTL = 60 * 15 # 15 Minutes

class YFinanceProvider(MarketDataProvider):
    def __init__(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

    def _get_cache_path(self, ticker: str, data_type: str) -> str:
        return os.path.join(CACHE_DIR, f"{ticker}_{data_type}.json")

    def _load_cache(self, path: str, ttl: int) -> Dict:
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Check TTL
            timestamp = data.get('provenance', {}).get('timestamp_epoch', 0)
            if time.time() - timestamp < ttl:
                data['provenance']['source'] += " (Cached)"
                return data
        except:
            pass
        return None

    def _save_cache(self, path: str, data: Dict):
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Cache write error: {e}")

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper()
        cache_path = self._get_cache_path(ticker, 'fund')
        
        cached = self._load_cache(cache_path, FUNDAMENTALS_TTL)
        if cached: return cached

        # Fetch Live
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract Key Metrics safely
            data = {
                "market_cap": info.get("marketCap", 0),
                "total_cash": info.get("totalCash", 0),
                "total_debt": info.get("totalDebt", 0),
                "ebitda": info.get("ebitda", 0),
                "revenue_growth": info.get("revenueGrowth", 0),
                "shares_outstanding": info.get("sharesOutstanding", 0),
                "previous_close": info.get("previousClose", 0),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                "sector": info.get("sector", "Unknown"),
                "profit_margins": info.get("profitMargins", 0.0),
                "operating_margins": info.get("operatingMargins", 0.0),
                "beta": info.get("beta", 1.0),
                "roe": info.get("returnOnEquity", 0.0),
                "provenance": {
                    "source": "yfinance",
                    "timestamp": datetime.now().isoformat(),
                    "timestamp_epoch": time.time()
                }
            }
            
            self._save_cache(cache_path, data)
            return data
        except Exception as e:
            print(f"YFinance Error ({ticker}): {e}")
            return {"error": str(e), "provenance": {"source": "error"}}

    def get_snapshot(self, tickers: List[str]) -> Dict[str, Dict]:
        # YFinance can fetch batch, but returns a DataFrame often.
        # For simplicity and caching, we iterate (as caching handles speed).
        # Optimization: use `yf.download(tickers, period='1d')` for pure price.
        # But we need cache.
        results = {}
        for t in tickers:
            # Re-using fundamentals logic for basic snapshot info (price often in info)
            # Or fetch specifically.
            pass 
        return {} # Not fully needed if we use get_fundamentals for "Deal Radar" logic

    def get_sparkline(self, ticker: str, days: int = 90) -> List[float]:
        ticker = ticker.upper()
        cache_path = self._get_cache_path(ticker, f'spark_{days}')
        
        cached = self._load_cache(cache_path, PRICE_TTL) # Price TTL
        if cached: return cached['data']

        import random
        
        # Retry Logic for Rate Limits
        for attempt in range(3):
            try:
                stock = yf.Ticker(ticker)
                # Use standard '3mo' to be safe, or mapping
                hist = stock.history(period="3mo")
                
                if hist.empty:
                    # Retry if empty (sometimes happens transiently)
                    time.sleep(random.uniform(0.5, 1.5))
                    continue
                
                prices = hist['Close'].tolist()
                
                data = {
                    "data": prices,
                    "provenance": {
                        "source": "yfinance",
                        "timestamp": datetime.now().isoformat(),
                        "timestamp_epoch": time.time()
                    }
                }
                self._save_cache(cache_path, data)
                return prices
                
            except Exception as e:
                # Exponential Backoff
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Sparkline Retry {attempt+1}/3 ({ticker}): {e} - Sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        print(f"Sparkline Failed ({ticker}) after 3 attempts.")
        return []
