import os
import sys
import json
from dotenv import load_dotenv

# Load env before importing service
load_dotenv()

from src.analysis.gemini_dossier import dossier_service

def test_adbe_dossier():
    print("--- Verifying ADBE Dossier Generation (Augmented) ---")
    
    # Mock payload simulating sparse data to trigger "Augmented Intelligence"
    # This mimics the state where retrieval service failing or returning old data
    payload = {
        "ticker": "ADBE",
        "name": "Adobe Inc.",
        "retrieved_items": [] 
    }
    
    # Force refresh to adhere to new prompt
    print(f"Generating dossier for {payload['ticker']} using model: {dossier_service.MODEL_NAME}...")
    result = dossier_service.generate_dossier("ADBE", payload, force_refresh=True)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    dossier = result.get("dossier", {})
    
    print("\n--- GENERATED CONTENT ---")
    print(f"Model Used: {result.get('metadata', {}).get('model', 'Unknown')}")
    
    print("\n[WHY IT MATTERS NOW]")
    for item in dossier.get("why_it_matters_now", []):
        print(f"- {item['bullet']} (Refs: {item.get('source_refs')})")

    print("\n[M&A POSTURE]")
    posture = dossier.get("mna_posture", {})
    print(f"Label: {posture.get('label')}")
    print(f"Confidence: {posture.get('confidence')}")
    print("\n[DEAL USAGE]")
    deal_fit = dossier.get("deal_fit", {})
    
    print("Recommended:")
    for item in deal_fit.get("recommended", []):
        print(f"  - TYPE: {item.get('type')}")
        print(f"    WHY:  {item.get('why')}")

    print("Avoid:")
    for item in deal_fit.get("avoid", []):
        print(f"  - TYPE: {item.get('type')}")
        print(f"    WHY:  {item.get('why')}")

if __name__ == "__main__":
    test_adbe_dossier()
