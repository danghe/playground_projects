from google import genai
from google.genai import types

print("Attributes in google.genai.types:")
for x in dir(types):
    if "Search" in x or "Tool" in x:
        print(f" - {x}")
