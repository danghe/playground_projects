
import json
import sys
from app import app

def verify_ssnc_pinning():
    print("Verifying SSNC Pinning Logic...")
    
    # 1. Test Market Map Endpoint
    client = app.test_client()
    with app.app_context():
        try:
            r = client.get('/api/v2/market-map?sector=Tech')
            if r.status_code == 200:
                data = json.loads(r.data)
                
                # Check Sellers
                sellers = data.get('sellers', [])
                if not sellers:
                    print("FAILED: No sellers returned")
                    return False
                    
                first_seller = sellers[0]
                if first_seller.get('ticker') == 'SSNC':
                    print(f"SUCCESS: Top Seller is SSNC (Type: {first_seller.get('seller_type')})")
                else:
                    print(f"FAILED: Top Seller is {first_seller.get('ticker')}, expected SSNC")
                    return False
                    
                # Check Buyers
                buyers = data.get('buyers', [])
                if not buyers:
                    print("FAILED: No buyers returned")
                    return False
                    
                first_buyer = buyers[0]
                if first_buyer.get('ticker') == 'SSNC':
                    print(f"SUCCESS: Top Buyer is SSNC (BR: {first_buyer.get('br')})")
                else:
                    print(f"FAILED: Top Buyer is {first_buyer.get('ticker')}, expected SSNC")
                    return False

            else:
                print(f"FAILED: Endpoint returned {r.status_code}")
                return False

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    # 2. Naive HTML Check for Classes
    try:
        with open("templates/deal_command.html", "r", encoding='utf-8') as f:
            html = f.read()
            if 'class="col-span-7 flex flex-col glass-panel rounded-lg shadow-sm h-full min-h-0"' in html:
                print("SUCCESS: HTML contains scrolling fix classes (h-full min-h-0)")
            else:
                print("FAILED: HTML missing scrolling fix classes")
                return False
    except Exception as e:
        print(f"ERROR reading HTML: {e}")
        return False

    print("ALL CHECKS PASSED")
    return True

if __name__ == "__main__":
    if verify_ssnc_pinning():
        sys.exit(0)
    else:
        sys.exit(1)
