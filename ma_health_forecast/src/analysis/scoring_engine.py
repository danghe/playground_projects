import sqlite3
import yaml
import os
import json
import sys
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.data.schema import get_db_path
from src.data.financing_loader import FinancingLoader

class ScoringEngine:
    """
    Modules B & C: Seller & Buyer Maps.
    Glass-Box Scoring with Audit-Grade transparency.
    Updated for Deltas 5-8 (Real Sellers/Buyers).
    """
    
    def __init__(self):
        self.db_path = get_db_path()
        self.config = self._load_config()
        self.adjacency = self._load_adjacency()
        self.anchors = self._load_anchors()

    def _load_config(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            with open(os.path.join(base_dir, 'config', 'score_weights.yaml'), 'r') as f:
                return yaml.safe_load(f)
        except:
            return {}

    def _load_anchors(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            with open(os.path.join(base_dir, 'config', 'anchors.yaml'), 'r') as f:
                return yaml.safe_load(f)
        except:
            return {}

    def _load_adjacency(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            with open(os.path.join(base_dir, 'config', 'adjacency.yaml'), 'r') as f:
                return yaml.safe_load(f)
        except:
            return {}

    def run_scoring_cycle(self, sector=None):
        print("Starting Scoring Cycle (v2.1 Real Maps)...")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 0. Get Macro Financing State
        macro_loader = FinancingLoader()
        macro_data = macro_loader.get_latest_financing()
        # High spread -> Higher debt stress weight
        stress_multiplier = 1.0
        if macro_data.get('hy_spread', 0) > 5.0:
            stress_multiplier = 1.2
        
        # Adjusted Dry Powder Logic would go here
        
        # 1. Fetch Public Companies
        query = """
            SELECT c.ticker, c.sector, c.sub_sector, c.market_cap, c.company_name,
                   f.cash, f.total_debt, f.ebitda_ttm, f.revenue_yoy, f.fcf_ttm
            FROM companies c
            LEFT JOIN fundamentals f ON c.ticker = f.ticker
        """
        if sector and sector != 'All':
            if sector == "Tech": sector = "Technology" # DB Mapping Fix
            query += f" WHERE c.sector = '{sector}'"
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        count = 0
        for row in rows:
            scores = self._calculate_scores(row, stress_multiplier)
            self._save_scores(cursor, row['ticker'], scores)
            count += 1
            
        # 2. Sync Sponsors
        self._sync_sponsors(cursor)
            
        conn.commit()
        conn.close()
        print(f"Scored {count} companies.")

    def _calculate_scores(self, row, stress_multiplier):
        # Unpack
        ticker = row['ticker']
        sector = row['sector']
        cash = row['cash'] or 0.0
        debt = row['total_debt'] or 0.0
        ebitda = row['ebitda_ttm'] or 0.0
        rev_growth = row['revenue_yoy'] or 0.0
        fcf = row['fcf_ttm'] or 0.0
        mcap = row['market_cap'] or 0.0
        
        # --- Configs ---
        spi_cfg = self.config.get('spi', {})
        br_cfg = self.config.get('buyer_readiness', {})
        
        # --- SPI Calculation (Seller Pressure) ---
        fsp_score = 0
        fsp_drivers = []
        ssi_score = 0
        
        # 1. Financial Stress (Forced Seller Signals)
        # Leverage
        leverage = debt / ebitda if ebitda > 0 else 0
        if leverage > 4.5:
             score_impact = 40 * stress_multiplier
             fsp_score += score_impact
             fsp_drivers.append(f"High Leverage ({leverage:.1f}x)")
        elif leverage > 3.0:
             fsp_score += 15
             
        # Liquidity / Refi Proxy (Maturity Wall Proxy)
        # If Debt > 0 and Cash < 10% of debt and FCF < 0 -> High Refi Risk
        if debt > 0 and (cash / debt) < 0.1 and fcf < 0:
            fsp_score += 35 * stress_multiplier
            fsp_drivers.append("Liquidity Crunch (Refi Risk)")
        
        # Price Distress (Proxy) - assuming we had price data, for now use valuation proxy
        # Low EV/EBITDA could imply distress
        ev_ebitda = (mcap + debt - cash) / ebitda if ebitda > 0 else 0
        if 0 < ev_ebitda < 5.0 and sector == 'Technology':
            fsp_score += 20
            fsp_drivers.append("Valuation Distress (<5x)")

        # 2. Strategic Stress (Strategic Seller Signals)
        # Growth Stall
        if rev_growth < 0.0:
            ssi_score += 30
            fsp_drivers.append(f"Revenue Contraction ({rev_growth*100:.1f}%)")
        elif rev_growth < 0.05:
            ssi_score += 15
            fsp_drivers.append("Growth Stall")
            
        # Carve-out signal (Conglomerate discount proxy - if large and low growth)
        if mcap > 50e9 and rev_growth < 0.05:
            ssi_score += 20
            fsp_drivers.append(f"Portfolio Review Candidate")
            
        # Weighted Final SPI
        final_spi = (fsp_score * spi_cfg.get('weights', {}).get('fsp', 0.65)) + \
                    (ssi_score * spi_cfg.get('weights', {}).get('ssi', 0.35))
        final_spi = min(100, final_spi)
        
        # --- 5. Determine Seller Type & Asset Type ---
        seller_type = "Opportunistic"
        likely_asset_type = "Wholeco" # Default
        
        # Combine all drivers for easier keyword search
        all_drivers = fsp_drivers # For now, only FSP drivers are detailed enough for asset type
        
        # Classify based on SPI score AND driver keywords
        # Use lower thresholds to reflect realistic scoring distribution
        if final_spi >= 40 or any("Refi" in d or "Liquidity" in d or "Covenant" in d for d in all_drivers):
            seller_type = "🔥 Forced Seller"
        elif final_spi >= 30 or any("Strategic" in d or "Review" in d or "Growth Stall" in d for d in all_drivers):
            seller_type = "📉 Strategic Review"
        elif final_spi >= 25:
            seller_type = "📉 Strategic Review"  # Still strategic if elevated
        
        # Check for specific drivers that indicate asset type
        if "Portfolio Review Candidate" in all_drivers:
             seller_type = "✂️ Structural Seller"
             likely_asset_type = "Carve-out"
        
        # Refine Asset Type based on keywords
        if "Conglomerate Discount" in all_drivers: # This driver is not explicitly added in current code, but if it were, it would trigger.
            likely_asset_type = "Spin-off / Carve-out"
        if "Liquidity Crunch (Refi Risk)" in all_drivers:
            likely_asset_type = "Accelerated Sale"
        # "Activist Pressure" is not currently a driver, but if added, would trigger.
        # if "Activist Pressure" in all_drivers:
        #     likely_asset_type = "Divestiture / Sale"

        # --- Buyer Readiness Calculation ---
        capacity_score = 0
        motive_score = 0
        br_drivers = []
        
        # 1. Capacity
        firepower = max(0, cash + (3 * ebitda) - debt)
        if mcap > 0:
            # Relative firepower
            fp_ratio = firepower / mcap
            capacity_score = min(100, fp_ratio * 50)
            if fp_ratio > 0.3:
                br_drivers.append(f"High Firepower (${firepower/1e9:.1f}B)")
        
        # Leverage Headroom
        if leverage < 2.0:
            capacity_score += 20
            br_drivers.append("Low Leverage (<2x)")
            
        # 2. Motive
        # Growth Stall triggers M&A need
        if rev_growth < 0.10: # Below 10% for tech is stall
             motive_score += 40
             br_drivers.append("Growth Stall (Needs M&A)")
             
        # "What they'll buy" (Adjacency)
        # Get sector themes
        themes = self.adjacency.get('adjacencies', {}).get(sector, [])
        if themes:
            br_drivers.append(f"Targeting: {', '.join(themes[:2])}")

        final_br = (capacity_score * br_cfg.get('weights', {}).get('capacity', 0.6)) + \
                   (motive_score * br_cfg.get('weights', {}).get('motive', 0.4))
        final_br = min(100, final_br)

        return {
            "spi": final_spi,
            "seller_type": seller_type,
            "buyer_readiness": final_br,
            "firepower": firepower,
            "spi_drivers": fsp_drivers,
            "br_drivers": br_drivers
        }

    def _save_scores(self, cursor, ticker, scores):
        # We need to add 'seller_type' to the scores table or just store in drivers
        # For now, let's append it to drivers or use a new column if we had one.
        # But wait, schema has fixed columns. 
        # I will store seller_type in the JSON driver as a hack if I can't add column, 
        # OR I should have added it in update_db. 
        # Actually, let's just prepend it to the driver list so it shows up in UI.
        
        spi_drivers = scores['spi_drivers']
        if scores['seller_type'] != "Opportunistic":
            spi_drivers.insert(0, f"TYPE: {scores['seller_type']}")
            
        cursor.execute("""
            INSERT OR REPLACE INTO scores (
                ticker, as_of, spi, buyer_readiness, capacity, 
                spi_drivers_json, br_drivers_json
            ) VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
        """, (
            ticker, scores['spi'], scores['buyer_readiness'], scores['firepower'],
            json.dumps(spi_drivers), json.dumps(scores['br_drivers'])
        ))

    def _sync_sponsors(self, cursor):
        sponsors = self.anchors.get('sponsors', {})
        for name, data in sponsors.items():
            cursor.execute("""
                INSERT OR REPLACE INTO sponsors (
                    name, est_dry_powder_usd, source_note, last_updated
                ) VALUES (?, ?, ?, ?)
            """, (
                name, data['est_dry_powder_usd'], 
                data['source_note'], data['last_updated']
            ))

if __name__ == "__main__":
    engine = ScoringEngine()
    engine.run_scoring_cycle()
