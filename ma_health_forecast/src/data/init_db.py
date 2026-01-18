import sqlite3
import os
import sys

# Ensure src is in path to import schema
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.schema import get_schema, get_db_path

def init_db():
    db_path = get_db_path()
    schema = get_schema()
    
    print(f"Initializing database at {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Execute schema
        cursor.executescript(schema)
        
        conn.commit()
        conn.close()
        print("Database initialization complete.")
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
