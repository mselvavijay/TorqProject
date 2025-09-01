import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/models"

headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("Error fetching models:", response.status_code, response.text)
else:
    models = response.json().get("models", [])
    print("Available Mistral models:")
    for model in models:
        if "mistral" in model["id"].lower():   # filter only Mistral models
            print("-", model["id"])
