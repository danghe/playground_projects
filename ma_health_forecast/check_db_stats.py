import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('src/data/ma_health.db')
    cursor = conn.cursor()
    
    print("--- DATABASE STATISTICS ---")
    
    # 1. Total Universe
    total = cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    print(f"Total Companies in DB: {total}")
    
    # 2. Sector Breakdown
    print("\n--- SECTOR BREAKDOWN ---")
    sectors = cursor.execute("SELECT sector, COUNT(*) FROM companies GROUP BY sector").fetchall()
    for s, c in sectors:
        print(f"{s}: {c}")
        
    # 3. Scored Universe (Sellers)
    print("\n--- SCORED SELLERS (SPI >= 20) ---")
    scored_sellers = cursor.execute("SELECT c.sector, COUNT(*) FROM scores s JOIN companies c ON s.ticker=c.ticker WHERE s.spi >= 20 GROUP BY c.sector").fetchall()
    for s, c in scored_sellers:
        print(f"{s}: {c}")

    # 4. Scored Buyers (BR >= 20)
    print("\n--- SCORED BUYERS (BR >= 20) ---")
    scored_buyers = cursor.execute("SELECT c.sector, COUNT(*) FROM scores s JOIN companies c ON s.ticker=c.ticker WHERE s.buyer_readiness >= 20 GROUP BY c.sector").fetchall()
    for s, c in scored_buyers:
        print(f"{s}: {c}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
