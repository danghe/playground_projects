import requests
import yaml
import sqlite3
import os
import json
import urllib.parse
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.data.schema import get_db_path

class NewsEngine:
    """
    Module D: Rumor & Special Situations.
    Targeted GDELT Sweeps with Trust Filtering.
    """
    GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self):
        self.db_path = get_db_path()
        self.config = self._load_config('news_queries.yaml')
        self.trusted = self._load_config('trusted_domains.yaml')
        self.trusted_domains = set(self.trusted.get('news', []) + self.trusted.get('pr', []))

    def _load_config(self, filename):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            with open(os.path.join(base_dir, 'config', filename), 'r') as f:
                return yaml.safe_load(f)
        except:
            return {}

    def run_rumor_sweep(self, tickers):
        print(f"Starting Rumor Sweep for {len(tickers)} tickers...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        keywords = self.config.get('keywords', {}).get('mna', [])
        
        count = 0
        conf_count = 0
        
        # Batch tickers
        chunk_size = 5
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i+chunk_size]
            query = self._build_query(chunk, keywords)
            
            # Fetch
            articles = self._fetch_gdelt(query)
            
            for art in articles:
                event = self._normalize_event(art, chunk)
                if event:
                    self._save_event(cursor, event)
                    count += 1
                    if event['confidence_label'] == 'TRUSTED':
                        conf_count += 1
                        
        conn.commit()
        conn.close()
        print(f"Rumor Sweep Complete. Found {count} signals ({conf_count} TRUSTED).")

    def _build_query(self, tickers, keywords):
        # (("Company A" OR "Company B") AND ("merger" OR "acquisition"))
        # Using strict phrases for company names/tickers might be brittle in GDELTv2 doc API
        # but let's try.
        
        t_part = " OR ".join([f'"{t}"' for t in tickers])
        k_part = " OR ".join([f'"{k}"' for k in keywords])
        
        # Encoded query is handled by requests params usually, but GDELT is picky
        full_q = f"({t_part}) ({k_part}) sourcelang:eng"
        return full_q

    def _fetch_gdelt(self, query):
        try:
            params = {
                'query': query,
                'mode': 'ArtList',
                'maxrecords': 50,
                'format': 'json',
                'sort': 'DateDesc'
            }
            resp = requests.get(self.GDELT_URL, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('articles', [])
        except Exception as e:
            print(f"GDELT Error: {e}")
        return []

    def _normalize_event(self, art, potential_tickers):
        # Deduce ticker mention (naive)
        title = art.get('title', '')
        url = art.get('url', '')
        domain = art.get('domain', '')
        
        mentioned_ticker = None
        for t in potential_tickers:
            if t in title or t in url: # Naive
                mentioned_ticker = t
                break
        
        if not mentioned_ticker: return None
        
        # Trust Logic
        confidence = "UNCONFIRMED"
        for td in self.trusted_domains:
            if td in domain:
                confidence = "TRUSTED"
                break
        
        return {
            "event_id": f"GDELT_{art.get('urlhash', datetime.now().timestamp())}",
            "ticker": mentioned_ticker,
            "date": art.get('seendate', datetime.now().isoformat())[:10],
            "type": "DealRumor",
            "source": "News",
            "confidence": confidence,
            "url": url,
            "domain": domain,
            "title": title
        }

    def _save_event(self, cursor, evt):
        try:
             cursor.execute("""
                INSERT OR IGNORE INTO events (
                    event_id, ticker, event_date, event_type, source_type,
                    confidence_label, source_url, source_domain, title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
             """, (
                 evt['event_id'], evt['ticker'], evt['date'], evt['type'],
                 evt['source'], evt['confidence'], evt['url'], evt['domain'], evt['title']
             ))
        except Exception as e:
             # print(f"DB Error: {e}")
             pass

if __name__ == "__main__":
    engine = NewsEngine()
    # Test with major deal magnets
    engine.run_rumor_sweep(['MSFT', 'Google', 'Apple', 'Salesforce', 'NVIDIA'])
