import os
from dotenv import load_dotenv
from google import genai

# Load env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    exit(1)

client = genai.Client(api_key=api_key)

print("--- Available Gemini Models ---")
try:
    for m in client.models.list():
        # Debug: Print the object dir if needed, but for now just try to print name
        if "gemini" in m.name:
            print(f"- {m.name} ({getattr(m, 'display_name', 'No Display Name')})")
            # print(dir(m)) # Uncomment to debug attributes if needed
except Exception as e:
    print(f"Error listing models: {e}")
