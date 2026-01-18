
import json
import sys
from app import app

def test_v2_market_map():
    client = app.test_client()
    url = "/api/v2/market-map?sector=Tech"
    try:
        r = client.get(url)
        if r.status_code != 200:
            print(f"FAILED: Status {r.status_code}")
            return False
            
        data = json.loads(r.data)
        
        # 1. Supply Checks
        sellers = data.get('sellers', [])
        if not sellers:
            print("WARNING: No sellers returned (might be empty DB)")
            # Even if empty, we can verify the structure of the response keys if we had any
        else:
            s = sellers[0]
            print(f"Sample Seller: {s.get('ticker')} - {s.get('name')}")
            
            # Check Keys
            required = ['ticker', 'name', 'sub_sector', 'seller_type', 'metrics', 'confidence']
            for k in required:
                if k not in s:
                    print(f"FAILED: Missing key {k} in seller")
                    return False
            
            # Check Metrics
            m = s.get('metrics', {})
            if 'net_leverage' not in m or 'price_dislocation' not in m:
                print("FAILED: Missing metrics structure")
                return False
                
            print("OK: Supply Structure verified.")

        # 2. Demand Checks
        buyers = data.get('buyers', [])
        if not buyers:
             print("WARNING: No buyers returned")
        else:
             b = buyers[0]
             print(f"Sample Buyer: {b.get('ticker')} - {b.get('br')}")
             
             # Check Sanitization
             if not isinstance(b.get('br'), int):
                 print(f"FAILED: BR is not int: {type(b.get('br'))}")
                 return False
                 
             if b.get('br') < 0 or b.get('br') > 100:
                 print(f"FAILED: BR out of range: {b.get('br')}")
                 return False
                 
             if not isinstance(b.get('firepower'), (int, float)):
                 print("FAILED: Firepower is not number")
                 return False
                 
             print("OK: Demand Structure verified.")
             
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Verifying Deal Command Upgrades (Test Client)...")
    with app.app_context():
        if test_v2_market_map():
            print("ALL CHECKS PASSED")
            sys.exit(0)
        else:
            print("VERIFICATION FAILED")
            sys.exit(1)
