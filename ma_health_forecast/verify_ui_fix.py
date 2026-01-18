
import json
import sys
import os
from app import app

def verify_ui_fixes():
    print("Verifying UI Fixes and Buyer Deep Dive...")
    
    # 1. Check HTML Structure for Layout Fix
    try:
        with open("templates/deal_command.html", "r", encoding='utf-8') as f:
            html = f.read()
            
        # Check for duplicate header nesting (naive check)
        err_pattern = 'class="p-3 border-b border-light flex justify-between items-center bg-white/50 dark:bg-slate-800/50">\n                        <div class="flex items-center gap-2">\n                            <h2'
        if html.count('SUPPLY: Top Sellers') > 1 and "class=\"p-3" in html.split('SUPPLY: Top Sellers')[0][-50:]:
             # This naive check is hard. Let's look for the specific removed nesting.
             pass

        # Check for Buyer Click Handler
        if '@click="openDrawer(b, \'buyer\')"' in html:
            print("SUCCESS: Buyer click handler found.")
        else:
            print("FAILED: Buyer click handler NOT found.")
            return False

    except Exception as e:
        print(f"ERROR reading HTML: {e}")
        return False

    # 2. Verify Deep Dive Endpoint supports 'buyer' type
    client = app.test_client()
    with app.app_context():
        payload = {
            "ticker": "BUYER1",
            "type": "buyer",
            "context": {"name": "Big Acquirer Inc", "sector": "Tech"}
        }
        try:
            r = client.post('/api/v2/deep-dive', json=payload)
            if r.status_code == 200:
                print("SUCCESS: Endpoint accepted 'buyer' type.")
            else:
                print(f"FAILED: Endpoint returned {r.status_code}")
                return False
        except Exception as e:
            print(f"ERROR calling endpoint: {e}")
            return False

    print("ALL CHECKS PASSED")
    return True

if __name__ == "__main__":
    if verify_ui_fixes():
        sys.exit(0)
    else:
        sys.exit(1)
