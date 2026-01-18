import os
import requests
import datetime
import sqlite3
import pandas as pd
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.data.schema import get_db_path

class FinancingLoader:
    """
    Fetches macro financing data (FRED) and computes Refi Risk proxies.
    """
    
    # FRED Series IDs
    SERIES_MAP = {
        'HY_SPREAD': 'BAMLH0A0HYM2', # ICE BofA US High Yield Index Option-Adjusted Spread
        'IG_SPREAD': 'BAMLC0A0CM',   # ICE BofA US Corporate Index Option-Adjusted Spread
        'C_AND_I_LOANS': 'BUSLOANS', # Commercial and Industrial Loans
    }
    
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY")
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        self.db_path = get_db_path()

    def fetch_series(self, series_id: str) -> float:
        """Fetch latest value from FRED."""
        if not self.api_key:
            # Fallback for dev if no key
            defaults = {'BAMLH0A0HYM2': 3.8, 'BAMLC0A0CM': 1.1, 'BUSLOANS': 2800.0}
            return defaults.get(series_id, 0.0)

        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': 1,
            'sort_order': 'desc'
        }
        try:
            r = requests.get(self.base_url, params=params)
            r.raise_for_status()
            data = r.json()
            if 'observations' in data and data['observations']:
                val = float(data['observations'][0]['value'])
                return val
        except Exception as e:
            print(f"Error fetching {series_id}: {e}")
            defaults = {'BAMLH0A0HYM2': 3.5, 'BAMLC0A0CM': 1.1, 'BUSLOANS': 2800.0}
            return defaults.get(series_id, 0.0)
        return 0.0

    def compute_lbo_feasibility(self, hy_spread: float) -> tuple:
        """
        Compute LBO Feasibility Index (0-100) and Leverage Range.
        Lower spread = Higher feasibility.
        """
        index = 0
        lev_range = "3.0x - 4.0x"
        
        if hy_spread < 3.0:
            index = 92
            lev_range = "6.0x - 7.0x"
        elif hy_spread < 4.0:
            index = 78
            lev_range = "5.0x - 6.0x"
        elif hy_spread < 5.5:
            index = 60
            lev_range = "4.0x - 5.0x"
        else:
            index = 40
            lev_range = "< 4.0x"
            
        return index, lev_range

    def update_macro_db(self):
        """Fetch data and update financing_macro table."""
        print("Updating Financing Macro Data...")
        hy = self.fetch_series(self.SERIES_MAP['HY_SPREAD'])
        ig = self.fetch_series(self.SERIES_MAP['IG_SPREAD'])
        
        lbo_idx, lev_range = self.compute_lbo_feasibility(hy)
        
        today = datetime.date.today()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO financing_macro (date, hy_spread, ig_spread, lbo_feasibility_index, expected_leverage_range)
            VALUES (?, ?, ?, ?, ?)
        """, (today, hy, ig, lbo_idx, lev_range))
        conn.commit()
        conn.close()
        print(f"Financing Updated: HY={hy}%, LBO Index={lbo_idx}, Lev={lev_range}")
        
    def get_latest_financing(self) -> Dict[str, Any]:
        """Retrieve latest record."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM financing_macro ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        else:
            return {
                "hy_spread": 4.0,
                "ig_spread": 1.2,
                "lbo_feasibility_index": 65,
                "expected_leverage_range": "4.5x - 5.5x"
            }

if __name__ == "__main__":
    loader = FinancingLoader()
    loader.update_macro_db()
