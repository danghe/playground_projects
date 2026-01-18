import os
from dotenv import load_dotenv
from google import genai

print("--- Gemini API Test (google-genai SDK) ---")

# 1. Load .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment variables.")
    exit(1)
else:
    print(f"API Key found: {api_key[:5]}...{api_key[-5:]}")

# 2. Configure Client
try:
    client = genai.Client(api_key=api_key)
    print("Client initialized successful.")
except Exception as e:
    print(f"ERROR: Client initialization failed: {e}")
    exit(1)

# 3. Test Generation
print("Attempting to generate content with gemini-2.0-flash-exp...")
try:
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents="Say 'Hello, World!' if you can hear me."
    )
    print(f"Response: {response.text}")
    print("SUCCESS: API is working with new SDK.")
except Exception as e:
    print(f"ERROR: Generation failed: {e}")

