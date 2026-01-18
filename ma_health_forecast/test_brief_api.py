import json
from app import app

def test_brief_endpoint():
    print("--- Testing /api/industry-brief ---")
    client = app.test_client()
    
    payload = {
        "sector": "Tech",
        "sub_industry": "Software",
        "force_refresh": True
    }
    
    try:
        response = client.post('/api/industry-brief', 
                               data=json.dumps(payload),
                               content_type='application/json')
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print("Response JSON Keys:", list(data.keys()))
            if 'brief' in data:
                print("Brief - Executive Takeaways:", data['brief'].get('executive_takeaways', [])[:1])
                print("Brief - Trend Narrative:", json.dumps(data['brief'].get('trend_narrative', "MISSING"), indent=2))
            if 'metadata' in data:
                print("Metadata:", data['metadata'])
                
        else:
            print("Error Response:", response.data.decode())
            
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_brief_endpoint()
