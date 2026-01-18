import sqlite3
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.data.schema import get_db_path

class MatchEngine:
    """
    Delta 6: Portfolio-Aware Mandate Generator.
    Calculates bilateral fit scores between Buyers and Targets.
    """

    def __init__(self):
        self.db_path = get_db_path()

    def run_match_cycle(self, sector=None, limit_per_entity=10):
        print("Starting Match Engine Cycle...")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Fetch Candidates
        # Buyers: Top 50 by Buyer Readiness
        # Targets: Top 50 by SPI (Seller Pressure)
        # Filter by sector if provided
        
        sector_filter = f"AND c.sector = '{sector}'" if sector and sector != 'All' else ""
        if sector == "Tech": sector_filter = "AND c.sector = 'Technology'"

        # Get Buyers
        buy_q = f"""
            SELECT c.ticker, c.sector, c.market_cap, s.buyer_readiness, s.capacity, c.sub_sector
            FROM companies c
            JOIN scores s ON c.ticker = s.ticker
            WHERE s.buyer_readiness > 30 {sector_filter}
            ORDER BY s.buyer_readiness DESC
            LIMIT 50
        """
        buyers = cursor.execute(buy_q).fetchall()
        
        # Get Targets
        sell_q = f"""
            SELECT c.ticker, c.sector, c.market_cap, s.spi, c.sub_sector
            FROM companies c
            JOIN scores s ON c.ticker = s.ticker
            WHERE s.spi > 30 {sector_filter}
            ORDER BY s.spi DESC
            LIMIT 50
        """
        targets = cursor.execute(sell_q).fetchall()
        
        print(f"Matching {len(buyers)} Buyers x {len(targets)} Targets...")
        
        match_count = 0
        
        # O(N^2) but N is small (50x50=2500)
        for buyer in buyers:
            for target in targets:
                if buyer['ticker'] == target['ticker']: continue
                
                score, drivers, deal_type = self._calculate_fit(buyer, target)
                
                if score > 50: # Only save relevant matches
                    self._save_match(cursor, buyer['ticker'], target['ticker'], "Buyer", score, drivers, deal_type)
                    match_count += 1
                    
        conn.commit()
        conn.close()
        print(f"Match Cycle Complete. Generated {match_count} matches.")

    def _calculate_fit(self, buyer, target):
        score = 0
        drivers = []
        deal_type = "Strategic"
        
        # 1. Feasibility (Firepower vs EV)
        # target EV proxy = mcap (ignoring debt for speed, or assume 10% premium)
        target_v = target['market_cap'] * 1.2 
        firepower = buyer['capacity'] * 1.5 # Can stretch logic
        
        if firepower > target_v:
            score += 30
            drivers.append("Financially Feasible")
        elif firepower > (target['market_cap'] * 0.5):
            score += 10 # Bolt-on possible
            
        # 2. Adjacency / Sector Fit
        if buyer['sub_sector'] == target['sub_sector']:
            score += 30
            drivers.append(f"Sub-sector Match ({buyer['sub_sector']})")
            deal_type = "Consolidation"
        elif buyer['sector'] == target['sector']:
            score += 15
            drivers.append("Sector Adjacency")
            deal_type = "Expansion"
            
        # 3. Size Logic (Antitrust)
        # If both huge -> Penalty
        if buyer['market_cap'] > 100e9 and target['market_cap'] > 50e9:
            score -= 20
            drivers.append("Antitrust Risk")
            
        # 4. Seller Pressure Bonus
        if target['spi'] > 60:
            score += 20
            drivers.append("Motivated Seller")
            
        # 5. Deal Type Logic
        size_ratio = target['market_cap'] / buyer['market_cap'] if buyer['market_cap'] > 0 else 100
        if size_ratio < 0.05:
            deal_type = "Tuck-in"
        elif size_ratio > 0.5:
            deal_type = "Merger of Equals"
            
        return min(100, max(0, score)), drivers, deal_type

    def _save_match(self, cursor, co_ticker, cp_ticker, direction, score, drivers, deal_type):
        cursor.execute("""
            INSERT OR REPLACE INTO matches (
                company_ticker, counterparty_ticker, direction, 
                fit_score, drivers_json, suggested_deal_type
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (co_ticker, cp_ticker, direction, score, json.dumps(drivers), deal_type))

if __name__ == "__main__":
    engine = MatchEngine()
    engine.run_match_cycle(sector="All")
