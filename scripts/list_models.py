import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {"x-goog-api-key": api_key}

response = requests.get(url, headers=headers, timeout=30)
print("Status:", response.status_code)

data = response.json()
for model in data.get("models", []):
    if "generateContent" in model.get("supportedGenerationMethods", []):
        print(model["name"])
        