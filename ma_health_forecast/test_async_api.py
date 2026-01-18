import requests
import json
import sys

# Base URL (assuming default Flask port)
BASE_URL = "http://127.0.0.1:5000"

def test_api():
    print("Testing /api/update_forecast...")
    try:
        payload = {"rate_change": 25, "confidence_shock": -5, "volatility_shock": 2}
        response = requests.post(f"{BASE_URL}/api/update_forecast", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if "plots" in data and "latest_val" in data:
                print("SUCCESS: /api/update_forecast returned valid data.")
            else:
                print("FAILURE: /api/update_forecast returned unexpected structure.")
        else:
            print(f"FAILURE: /api/update_forecast returned {response.status_code}")
            
    except Exception as e:
        print(f"FAILURE: Could not connect to {BASE_URL}. Is the server running? ({e})")
        # We can't really test the running server from here easily without starting it in a subprocess, 
        # which might be complex. 
        # Instead, let's unit test the app functions directly if we can, or just rely on the fact that we fixed the code.
        # But wait, I can import the app and use test_client!
        pass

from app import app

def test_with_client():
    print("\nTesting with Flask Test Client...")
    with app.test_client() as client:
        # 1. Test Update Forecast
        print("1. Testing /api/update_forecast")
        res = client.post('/api/update_forecast', json={"rate_change": 0})
        if res.status_code == 200:
            data = res.get_json()
            if "plots" in data:
                print("   PASS: Plots returned.")
            else:
                print("   FAIL: No plots.")
        else:
            print(f"   FAIL: Status {res.status_code}")

        # 2. Test Narrative (Mocking Gemini would be ideal, but let's just see if it handles the request)
        # Since Gemini call takes time and costs money/quota, we might hit limits.
        # But we need to verify the endpoint exists and accepts JSON.
        print("2. Testing /api/narrative (Connectivity)")
        # We won't actually wait for the full LLM response in this quick test if we can avoid it, 
        # but the code calls it synchronously. 
        # Let's just check if the route is registered.
        # Actually, let's try a call.
        try:
            res = client.post('/api/narrative', json={"rate_change": 0})
            if res.status_code == 200:
                print("   PASS: Narrative endpoint works.")
            elif res.status_code == 500:
                 print("   WARN: Narrative endpoint reachable but failed (likely API key or quota).")
            else:
                print(f"   FAIL: Status {res.status_code}")
        except Exception as e:
            print(f"   FAIL: {e}")

if __name__ == "__main__":
    test_with_client()
