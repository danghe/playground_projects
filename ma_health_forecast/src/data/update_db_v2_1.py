import sqlite3
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.schema import get_db_path

def add_new_tables():
    db_path = get_db_path()
    print(f"Updating Database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Matches Table (Delta 6)
    print("Creating 'matches' table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        company_ticker TEXT,
        counterparty_ticker TEXT,
        direction TEXT, -- 'Buyer' or 'Target'
        fit_score REAL,
        drivers_json TEXT, -- JSON breakdown of score
        suggested_deal_type TEXT, -- 'Tuck-in', 'Take-Private', etc.
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (company_ticker, counterparty_ticker, direction)
    )
    ''')
    
    # 2. Debt Profile Table (Delta 7 - Maturity Wall)
    print("Creating 'debt_profile' table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS debt_profile (
        ticker TEXT PRIMARY KEY,
        as_of DATE,
        due_12m REAL, -- Debt maturing in 12 months (Proxy or Actual)
        due_24m REAL,
        due_36m REAL,
        extraction_confidence TEXT DEFAULT 'LOW', -- LOW (Proxy), HIGH (Parsed)
        source_accession TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 3. Financing Macro Table (Delta 7)
    print("Creating 'financing_macro' table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS financing_macro (
        date DATE PRIMARY KEY,
        hy_spread REAL,
        ig_spread REAL,
        lbo_feasibility_index REAL,
        expected_leverage_range TEXT, -- "4.5x - 5.5x"
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database Update Complete.")

if __name__ == "__main__":
    add_new_tables()
