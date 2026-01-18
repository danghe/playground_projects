import sqlite3
import os
import re

class EntityResolver:
    """
    Robust Entity Resolution Engine.
    Maps company names, aliases, and common variations to canonical Tickers.
    """
    
    def __init__(self, db_path=None):
        if not db_path:
            # Default to relative path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'data', 'ma_health.db')
        else:
            self.db_path = db_path
            
        self.index = {} # Map text -> ticker
        self.cik_map = {} # Map ticker -> cik
        self.load_index()
        
    def load_index(self):
        """Loads Entity Index from DB"""
        if not os.path.exists(self.db_path):
             # print(f"Warning: Database not found at {self.db_path}") 
             # Suppress warning on init if DB is empty/creating
             return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Load Companies (Ticker, Name) from DB
            # Check if table exists first to avoid error on fresh init
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
            if not cursor.fetchone():
                return

            cursor.execute("SELECT ticker, company_name, cik FROM companies")
            for row in cursor.fetchall():
                ticker, name, cik = row
                if not ticker: continue
                
                ticker = ticker.upper()
                self.index[ticker] = ticker # Self-map
                
                if name:
                    clean_name = self._normalize(name)
                    self.index[clean_name] = ticker
                
                if cik:
                    self.cik_map[ticker] = str(cik).zfill(10)
            
            # 2. Load Aliases
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_aliases'")
            if cursor.fetchone():
                cursor.execute("SELECT alias, ticker FROM company_aliases")
                for row in cursor.fetchall():
                    alias, ticker = row
                    if alias and ticker:
                        self.index[self._normalize(alias)] = ticker.upper()
                    
            conn.close()
            # print(f"Entity Index Loaded: {len(self.index)} entries")
            
        except Exception as e:
            print(f"Error loading entity index: {e}")

    def _normalize(self, text):
        """Standardizes text for matching"""
        if not text: return ""
        text = text.lower().strip()
        
        # Remove common suffixes
        text = re.sub(r'\b(inc|corp|corporation|ltd|llc|holdings|group|plc|company|co)\b\.?', '', text)
        
        # Remove special chars
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return text.strip()

    def resolve_ticker(self, text):
        """
        Resolves a search string to a Ticker.
        Returns: (Ticker, Confidence, MatchType) or (None, 0.0, None)
        """
        if not text: return None, 0.0, None
        
        # 1. Exact Ticker Match
        text_upper = text.upper().strip()
        if text_upper in self.index and self.index[text_upper] == text_upper:
            return text_upper, 1.0, 'Ticker (Exact)'
            
        # 2. Normalized Match
        norm_text = self._normalize(text)
        if norm_text in self.index:
            return self.index[norm_text], 0.9, 'Name/Alias (Exact)'
            
        # 3. Known Hardcoded Maps (Resilience)
        # These should eventually move to DB aliases, but helpful for hard start
        FALLBACK_MAP = {
            'google': 'GOOGL',
            'alphabet': 'GOOGL',
            'facebook': 'META',
            'meta': 'META',
            'fb': 'META',
            'microsoft': 'MSFT',
            'apple': 'AAPL',
            'amazon': 'AMZN',
            'netflix': 'NFLX',
            'tesla': 'TSLA',
            'nvidia': 'NVDA'
        }
        
        norm_text_lower = self._normalize(text)
        if norm_text_lower in FALLBACK_MAP:
             return FALLBACK_MAP[norm_text_lower], 0.95, 'Hardcoded Alias'
        
        return None, 0.0, None

    def get_cik(self, ticker):
         return self.cik_map.get(ticker.upper())

# Self-Test
if __name__ == "__main__":
    resolver = EntityResolver()
    
    test_cases = [
        "Google", "Alphabet Inc.", "META", "facebook", "TesLa", 
        "UnknownCorp", "NVDA", "NVIDIA Corporation"
    ]
    
    print("--- Entity Resolver Test ---")
    for t in test_cases:
        res, conf, reason = resolver.resolve_ticker(t)
        print(f"'{t}' -> {res} ({conf*100:.0f}%) [{reason}]")
