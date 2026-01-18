import requests
import json
import unittest

BASE_URL = "http://127.0.0.1:8080"  # Assuming standard Flask port

class TestV2Upgrade(unittest.TestCase):
    def test_market_map_structure(self):
        """Verify v2 market map returns playbook and enhanced sellers."""
        try:
            resp = requests.get(f"{BASE_URL}/api/v2/market-map?sector=Tech")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            
            # 1. Check Playbook
            self.assertIn("playbook", data, "Playbook key missing")
            self.assertIn("top_archetypes", data["playbook"], "Archetypes missing")
            self.assertTrue(len(data["playbook"]["top_archetypes"]) > 0, "No archetypes returned")
            
            # 2. Check Seller Enhancements
            sellers = data["sellers"]
            if sellers:
                s = sellers[0]
                self.assertIn("likely_asset_type", s, "Asset type missing")
                self.assertIn("drivers", s)
                # Check for numeric driver format (e.g. contains numbers/x/%)
                has_numeric = any(any(c.isdigit() for c in d) for d in s["drivers"])
                self.assertTrue(has_numeric, f"Drivers lack numeric data: {s['drivers']}")
                
            # 3. Check Buyer Sanity
            buyers = data["buyers"]
            for b in buyers:
                # Firepower should be raw USD (large number) or 0
                fp = b.get("firepower", 0)
                if fp > 0:
                    self.assertTrue(fp > 1000000, f"Firepower seems too small (not raw USD): {fp}")

        except requests.exceptions.ConnectionError:
            print("Skipping integration test - Server not running")

if __name__ == "__main__":
    unittest.main()
