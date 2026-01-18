import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_update_forecast():
    print("Testing /api/update_forecast...")
    payload = {
        "rate_change": "0",  # Frontend sends strings
        "confidence_shock": "0",
        "volatility_shock": "0",
        "include_ai": True
    }
    try:
        res = requests.post(f"{BASE_URL}/api/update_forecast", json=payload)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            plot_keys = data.get("plots", {}).keys()
            print(f"Keys: {list(data.keys())}")
            print(f"Plots: {list(plot_keys)}")
            
            # Check if AI forecast is present in the response
            # Note: The response structure for plots flattens everything? 
            # No, generate_dashboard_data returns a dict with 'plots'. 
            # The route returns jsonify(data).
            
            # We also want to know if 'ai_forecast' dataframe was used to generate the plot.
            # We can't check the image, but we can check if execution succeeded.
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Exception: {e}")

def test_narrative():
    print("\nTesting /api/narrative...")
    payload = {
        "rate_change": "0",
        "confidence_shock": "0",
        "volatility_shock": "0",
        "include_ai": True
    }
    try:
        res = requests.post(f"{BASE_URL}/api/narrative", json=payload)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print(f"Response: {res.json()}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_update_forecast()
    test_narrative()
