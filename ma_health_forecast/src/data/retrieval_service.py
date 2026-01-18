import yfinance as yf
from src.analysis.strategic_radar import StrategicSECMonitor
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class RetrievalService:
    """
    Audit-Grade Retrieval Service.
    - Sources: SEC (via StrategicSECMonitor), News (via yfinance)
    - Policy: No scraping unspecified sites. Trusted sources only.
    """
    
    def __init__(self):
        self.sec_monitor = StrategicSECMonitor()

    def retrieve_context(self, ticker: str):
        """
        Main entry point. Fetches and normalizes context from all trusted sources.
        Returns a dictionary compliant with Dossier Service payload.
        """
        retrieved_items = []
        company_name = ticker # Fallback
        
        # 1. SEC Filings (Audit-Grade)
        try:
            sec_items = self._fetch_sec_context(ticker)
            retrieved_items.extend(sec_items)
        except Exception as e:
            logger.error(f"SEC Fetch Error for {ticker}: {e}")

        # 2. News / IR (via yfinance)
        try:
            news_items = self._fetch_news_context(ticker)
            retrieved_items.extend(news_items)
            
            # Try to get better name from yfinance
            if news_items:
                # We don't get name from news items, but we can try fetching info
                # Optimization: Don't fetch info just for name if we can avoid it.
                # But Dossier wants a name.
                pass
        except Exception as e:
            logger.error(f"News Fetch Error for {ticker}: {e}")
            
        # 3. Sort by Recency
        retrieved_items.sort(key=lambda x: x['published_at'], reverse=True)
        
        return {
            "name": company_name,
            "items": retrieved_items,
            "ticker": ticker
        }

    def _fetch_sec_context(self, ticker: str):
        """
        Reuses StrategicSECMonitor to interpret SEC filings.
        Returns normalized items.
        """
        items = []
        
        # Use existing monitor to get raw filing history
        sec_data = self.sec_monitor.fetch_filing_history(ticker)
        if not sec_data: return []
        
        # Use existing analysis logic to identify catalysts
        catalysts, _, _ = self.sec_monitor.analyze_filings(ticker, sec_data)
        
        for cat in catalysts:
            items.append({
                "id": f"sec_{hashlib.md5(str(cat).encode()).hexdigest()[:8]}",
                "source_type": "SEC",
                "source_name": "SEC EDGAR",
                "title": cat.get('headline', cat['type']),
                "url": cat.get('link', ''),
                "published_at": cat['date'], # YYYY-MM-DD
                "snippet": cat.get('implication', ''),
                "tags": [cat['type'], "Regulatory"]
            })
            
        return items

    def _fetch_news_context(self, ticker: str):
        """
        Fetches trusted news via yfinance API.
        Limits to top 5 items.
        """
        items = []
        limit = 5
        
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news: return []
        
        for n in news[:limit]:
            # providerPublishTime is unix timestamp
            pub_ts = n.get('providerPublishTime', 0)
            pub_date = datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            
            items.append({
                "id": n.get('uuid', f"news_{pub_ts}"),
                "source_type": "News",
                "source_name": n.get('publisher', 'Financial News'),
                "title": n.get('title', ''),
                "url": n.get('link', ''),
                "published_at": pub_date,
                "snippet": f"Publisher: {n.get('publisher')}. Type: {n.get('type')}.",
                "tags": ["News", n.get('type', 'General')]
            })
            
        return items

    def compute_retrieval_hash(self, items):
        """Deterministic hash of retrieval result for caching"""
        canonical = json.dumps(items, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

# Singleton
retrieval_service = RetrievalService()
