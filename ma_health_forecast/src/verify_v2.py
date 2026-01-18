import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(name, url, method='GET', payload=None, stream=False):
    print(f"Testing {name}...", end=" ")
    try:
        if method == 'GET':
            res = requests.get(f"{BASE_URL}{url}", stream=stream, timeout=30)
        else:
            res = requests.post(f"{BASE_URL}{url}", json=payload, timeout=30)
        
        if res.status_code == 200:
            print("✅ OK")
            if stream:
                print("   (Stream detected)")
                for line in res.iter_lines():
                    if line:
                        print(f"   Sample: {line[:60]}...")
                        break
            elif 'application/json' in res.headers.get('Content-Type', ''):
                data = res.json()
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   Keys: {keys}")
                    
                    # Check for plots specifically
                    if 'plots' in data:
                        plot_keys = list(data['plots'].keys())
                        print(f"   Plots: {plot_keys} ({len(plot_keys)} total)")
                return data
            else:
                print(f"   Content-Type: {res.headers.get('Content-Type')}")
            return res
        else:
            print(f"❌ Failed ({res.status_code})")
            print(f"   {res.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("MACRO FORECAST / M&A INDEX VERIFICATION")
    print("=" * 60)
    
    # 1. Home Page (Template Render)
    test_endpoint("Home Page (GET)", "/")
    
    # 2. Dashboard API (Should return all 7 plots)
    data = test_endpoint("Dashboard API", "/api/update_forecast", method='POST', payload={
        "rate_change": 0,
        "confidence_shock": 0,
        "volatility_shock": 0,
        "include_ai": False
    })
    
    if data and 'plots' in data:
        expected_plots = ['plot_url', 'attribution_url', 'irf_url', 'history_url', 
                          'contributions_url', 'deal_activity_url', 'confidence_url']
        missing = [p for p in expected_plots if p not in data['plots']]
        if missing:
            print(f"   ⚠️ Missing plots: {missing}")
        else:
            print(f"   ✅ All 7 plots present!")
    
    # 3. Narrative API
    test_endpoint("Narrative API", "/api/narrative", method='POST', payload={
        "rate_change": 0,
        "include_ai": False
    })
    
    print("\n" + "=" * 60)
    print("DEAL RADAR VERIFICATION")
    print("=" * 60)
    
    # 4. Deal Radar Page
    test_endpoint("Deal Radar UI", "/deal-radar")
    
    # 5. SSE Stream
    test_endpoint("Radar Stream (SSE)", "/api/deal-radar/stream?sector=Tech", stream=True)
    
    # 6. Industry Brief
    test_endpoint("Industry Brief", "/api/industry-brief", method='POST', payload={
        "sector": "Tech",
        "sub_industry": "Software"
    })
    
    # 7. Company Dossier
    test_endpoint("Company Dossier", "/api/company-dossier", method='POST', payload={
        "ticker": "AAPL"
    })
    
    print("\n" + "=" * 60)
    print("DEAL COMMAND v2.1 VERIFICATION")
    print("=" * 60)
    
    # 8. Deal Command Page
    test_endpoint("Deal Command UI", "/deal-command")
    
    # 9. Market Map
    test_endpoint("Market Map API", "/api/v2/market-map?sector=Tech")
    
    # 10. Financing
    test_endpoint("Financing API", "/api/v2/financing")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
