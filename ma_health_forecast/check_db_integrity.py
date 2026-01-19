
import os
import sqlite3

db_path = 'src/data/ma_health.db'

print(f"Checking DB at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print("ERROR: ma_health.db not found!")
    exit(1)

size = os.path.getsize(db_path)
print(f"DB Size: {size} bytes")

if size == 0:
    print("ERROR: DB is 0 bytes.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    
    for t in tables:
        table = t[0]
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Table '{table}': {count} rows")
        
    print("\n--- Testing 'Technology' Sector Query (from app.py) ---")
    query = """
        SELECT c.ticker, c.company_name, c.market_cap,
               s.spi, s.buyer_readiness, s.capacity
        FROM companies c
        JOIN scores s ON c.ticker = s.ticker
        WHERE c.sector = 'Technology'
        ORDER BY s.spi DESC
        LIMIT 5
    """
    rows = cursor.execute(query).fetchall()
    print(f"Query Result Count: {len(rows)}")
    for r in rows:
        print(r)
        
    if len(rows) == 0:
        print("CRITICAL: Technology Query returned 0 rows! Check sector naming in 'companies' table.")
        # Debug sector names
        sectors = cursor.execute("SELECT DISTINCT sector FROM companies").fetchall()
        print(f"Available Sectors: {sectors}")
        
    conn.close()
    print("DB Check Complete: OK")
except Exception as e:
    print(f"DB Check Failed: {e}")
