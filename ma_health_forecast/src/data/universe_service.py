import json
import os
from typing import List, Dict, Optional

class UniverseService:
    """
    Manages the 'Source of Truth' universe from local Audit-Grade Store.
    Reads from: src/data/store/companies.json & fundamentals.json
    """
    
    STORE_DIR = os.path.join(os.path.dirname(__file__), 'store')
    UNIVERSE_FILE = os.path.join(STORE_DIR, 'companies.json')
    FUNDAMENTALS_FILE = os.path.join(STORE_DIR, 'fundamentals.json')

    def __init__(self):
        self.universe = self.load_universe()
        self.fundamentals = self.load_fundamentals()

    def load_universe(self) -> List[Dict]:
        """Loads the master company list."""
        if not os.path.exists(self.UNIVERSE_FILE):
            print(f"WARN: Universe Store not found at {self.UNIVERSE_FILE}. Run ingest_universe.py.")
            return []
        try:
            with open(self.UNIVERSE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading universe: {e}")
            return []

    def load_fundamentals(self) -> Dict[str, Dict]:
        """Loads the deep fundamentals map."""
        if not os.path.exists(self.FUNDAMENTALS_FILE):
            return {}
        try:
            with open(self.FUNDAMENTALS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading fundamentals: {e}")
            return {}

    # Sector Alias Map: UI names → Store names + variants
    SECTOR_ALIASES = {
        "Tech": ["Technology", "Tech", "Information Technology", "Communication Services"],
        "Technology": ["Technology", "Tech", "Information Technology", "Communication Services"],
        "Healthcare": ["Healthcare", "Health Care"],
        "Financial Services": ["Financial Services", "Financials", "Finance"],
        "Financials": ["Financial Services", "Financials", "Finance"],
        "Energy": ["Energy"],
        "Industrials": ["Industrials", "Industrial"],
        "Communication Services": ["Communication Services"],
    }

    def get_tickers(self, sector: str = None, sub_industry: str = None, limit: int = None) -> List[str]:
        filtered = self.universe
        if sector:
            # Match any alias for the sector
            valid_sectors = self.SECTOR_ALIASES.get(sector, [sector])
            filtered = [c for c in filtered if c.get('sector') in valid_sectors]
        if sub_industry:
            filtered = [c for c in filtered if c.get('sub_industry') == sub_industry]
            
        tickers = [c['ticker'] for c in filtered]
        if limit and limit > 0:
            return tickers[:limit]
        return tickers

    def get_company(self, ticker: str) -> Optional[Dict]:
        ticker = ticker.upper()
        # 1. Metadata
        meta = next((c for c in self.universe if c['ticker'] == ticker), None)
        if not meta: return None
        
        # 2. Merge Fundamentals if available
        fund = self.fundamentals.get(ticker, {})
        # Merge carefully to avoid overwriting key metadata
        full_data = {**fund, **meta} 
        return full_data

    def get_sector_map(self, sector: str) -> Dict[str, Dict]:
        """
        Returns O(1) map of all companies in sector, ENRICHED with fundamentals.
        """
        valid_sectors = self.SECTOR_ALIASES.get(sector, [sector])
        sector_map = {}
        for c in self.universe:
            if c.get('sector') in valid_sectors:
                ticker = c['ticker']
                fund = self.fundamentals.get(ticker, {})
                sector_map[ticker] = {**fund, **c}
        return sector_map

    def get_industry_heatmap(self, sector: str) -> List[Dict]:
        """
        Aggregates stats for the Heatmap.
        Returns list of {sub_industry, count, avg_mcap, ...}
        """
        valid_sectors = self.SECTOR_ALIASES.get(sector, [sector])
        # Bucket by sub_industry
        buckets = {}
        for c in self.universe:
            if c.get('sector') in valid_sectors:
                sub = c.get('sub_industry', 'Other')
                if sub not in buckets: buckets[sub] = []
                buckets[sub].append(c)
        
        results = []
        for sub, items in buckets.items():
            # Calculate simple aggregates
            # Note: For full momentum/SPI logic, the TrendEngine handles deeper analysis.
            # This service provides the structural grouping.
            results.append({
                "name": sub,  # Used for UI loop
                "count": len(items),
                "tickers": [x['ticker'] for x in items]
            })
        return results

    def get_stats(self):
        stats = {}
        for c in self.universe:
            sec = c.get('sector', 'Unknown')
            stats[sec] = stats.get(sec, 0) + 1
        return stats

    def get_available_sectors(self) -> List[str]:
        """Returns sorted sectors excluding 'Unknown' for dropdown display."""
        stats = self.get_stats()
        return sorted([s for s in stats.keys() if s.lower() != 'unknown'])

    def get_company_name(self, ticker: str) -> str:
        """
        Returns the best available company name for a ticker.
        Priority: short_name > title > long_name > ticker
        """
        for c in self.universe:
            if c['ticker'] == ticker:
                return (
                    c.get('short_name') or 
                    c.get('title') or 
                    c.get('long_name') or 
                    ticker
                )
        return ticker

    def get_diagnostics(self) -> Dict:
        """
        Returns data quality diagnostics:
        - Total universe size
        - Per-sector counts with completeness metrics
        - Unknown count and %
        """
        total = len(self.universe)
        stats = self.get_stats()
        
        unknown_count = stats.get('Unknown', 0)
        unknown_pct = (unknown_count / total * 100) if total > 0 else 0
        
        # Per-sector completeness
        sector_details = {}
        tech_sub_counts = {}
        confidence_breakdown = {'High': 0, 'Medium': 0, 'Low': 0, 'N/A': 0}
        
        for c in self.universe:
            sec = c.get('sector', 'Unknown')
            if sec not in sector_details:
                sector_details[sec] = {
                    'count': 0,
                    'with_name': 0,
                    'with_valuation': 0,
                    'with_volume': 0
                }
            
            sector_details[sec]['count'] += 1
            
            # Sub-Sector Tracking (Focus on Tech)
            if sec == 'Technology' or sec == 'Tech':
                sub = c.get('sub_industry', 'Unclassified')
                tech_sub_counts[sub] = tech_sub_counts.get(sub, 0) + 1
                
                # Confidence Tracking
                conf = c.get('classification_confidence', 'N/A')
                confidence_breakdown[conf] = confidence_breakdown.get(conf, 0) + 1
            
            # Check name (short_name or title)
            if c.get('short_name') or c.get('title'):
                sector_details[sec]['with_name'] += 1
            
            # Check valuation from fundamentals
            ticker = c['ticker']
            fund = self.fundamentals.get(ticker, {})
            if fund.get('valuation_score'):
                sector_details[sec]['with_valuation'] += 1
            if c.get('average_volume', 0) > 0 or fund.get('average_volume', 0) > 0:
                sector_details[sec]['with_volume'] += 1
        
        # Convert to percentages
        sectors = {}
        for sec, data in sector_details.items():
            cnt = data['count']
            sectors[sec] = {
                'count': cnt,
                'name_pct': (data['with_name'] / cnt * 100) if cnt > 0 else 0,
                'val_pct': (data['with_valuation'] / cnt * 100) if cnt > 0 else 0,
                'volume_pct': (data['with_volume'] / cnt * 100) if cnt > 0 else 0
            }
        
        return {
            'total_count': total,
            'unknown_count': unknown_count,
            'unknown_pct': unknown_pct,
            'sectors': sectors,
            'tech_breakdown': tech_sub_counts,
            'classification_confidence': confidence_breakdown
        }

