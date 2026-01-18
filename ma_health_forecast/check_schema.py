import sqlite3
import os

db_path = 'ma_health.db'

if not os.path.exists(db_path):
    print(f"Database file {db_path} does not exist!")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print(f"Tables in {db_path}:")
        for t in tables:
            print(f"- {t[0]}")
            
            # Print count for each table
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                print(f"  Count: {count}")
            except:
                print("  Count: Error")
                
        conn.close()
    except Exception as e:
        print(f"Error reading DB: {e}")
