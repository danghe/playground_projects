from app import app
import json
import sys
import os

# Add src to path just in case
sys.path.append(os.path.dirname(__file__))

def verify():
    print("Verifying V2 Routes...")
    client = app.test_client()
    
    routes = [
        '/command-center',
        '/api/v2/market-map?sector=Tech',
        '/api/v2/deal-tape',
        '/api/v2/rumors',
        '/api/v2/sponsors',
        '/api/v2/diagnostics'
    ]
    
    for r in routes:
        try:
            resp = client.get(r)
            status = resp.status_code
            print(f"{r}: {status}")
            if status != 200:
                print(f"Error in {r}: {resp.data}")
            else:
                 # Check content
                 if 'api' in r:
                     data = json.loads(resp.data)
                     if isinstance(data, list):
                         print(f"  > Returned {len(data)} items")
                     elif isinstance(data, dict):
                         print(f"  > Keys: {list(data.keys())}")
        except Exception as e:
            print(f"Failed {r}: {e}")

if __name__ == "__main__":
    verify()
