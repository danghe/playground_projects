import requests
import json
import sys

def test_deep_dive():
    url = "http://127.0.0.1:5001/api/deal-architect/deep-dive"
    payload = {
        "user_ticker": "CVS",
        "target_ticker": "RDY",
        "intent": "BUY",
        "mandate": "Adjacency"
    }
    
    try:
        print(f"Sending POST to {url}...")
        resp = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print("\nResponse Keys:", list(data.keys()))
            if 'memo_html' in data:
                print(f"memo_html length: {len(str(data['memo_html']))}")
                print(f"memo_html excerpt: {str(data['memo_html'])[:100]}")
            else:
                print("!!! memo_html key MISSING !!!")
                
            if 'verdict' in data:
                print(f"verdict: {data['verdict']}")
            else:
                print("!!! verdict key MISSING !!!")
        else:
            print("Error Response Text:")
            print(resp.text)
            
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    test_deep_dive()
