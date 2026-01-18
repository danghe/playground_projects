import json
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.data.schema import get_db_path

def sync_json_to_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    store_dir = os.path.join(base_dir, 'data', 'store')
    db_path = get_db_path()
    
    print(f"Syncing JSON Store from {store_dir} to {db_path}...")
    
    # Load JSON
    try:
        with open(os.path.join(store_dir, 'companies.json'), 'r') as f:
            companies = json.load(f)
        with open(os.path.join(store_dir, 'fundamentals.json'), 'r') as f:
            fundamentals = json.load(f)
    except Exception as e:
        print(f"Error reading JSON store: {e}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    comp_count = 0
    fund_count = 0
    
    for c in companies:
        try:
            # Companies Table
            cursor.execute("""
                INSERT OR REPLACE INTO companies (
                    ticker, cik, company_name, sector, sub_sector, 
                    market_cap, avg_daily_volume, classification_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c.get('ticker'), c.get('cik'), c.get('title') or c.get('short_name'),
                c.get('sector'), c.get('sub_industry'), c.get('market_cap'),
                c.get('average_volume'), c.get('classification_confidence')
            ))
            comp_count += 1
            
            # Fundamentals Table
            t = c.get('ticker')
            if t in fundamentals:
                f = fundamentals[t]
                # Map fields
                cursor.execute("""
                    INSERT OR REPLACE INTO fundamentals (
                        ticker, as_of, 
                        cash, total_debt, ebitda_ttm, revenue_yoy
                    ) VALUES (?, DATE('now'), ?, ?, ?, ?)
                """, (
                    t, 
                    f.get('total_cash'), f.get('total_debt'), 
                    f.get('ebitda'), f.get('revenue_growth')
                ))
                fund_count += 1
                
        except Exception as e:
            print(f"Error syncing {c.get('ticker')}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Sync Complete. Companies: {comp_count}, Fundamentals: {fund_count}")

if __name__ == "__main__":
    sync_json_to_db()
