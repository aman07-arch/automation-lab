import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()]

RETRY_CODES = (429, 500, 503, 504)  # temporary problems worth retrying


def ask_gemini(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        for attempt in range(1, 4):  # up to 3 tries per model
            try:
                response = requests.post(url, headers=headers, json=body, timeout=60)
            except requests.exceptions.RequestException as error:
                print(f"[{model}] try {attempt}: network problem ({type(error).__name__})")
                time.sleep(5 * attempt)
                continue

            if response.status_code == 200:
                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError):
                    print(f"[{model}] unexpected response: {data}")
                    break  # move on to the next model

            if response.status_code in RETRY_CODES:
                print(f"[{model}] try {attempt}: busy (status {response.status_code}), waiting...")
                time.sleep(5 * attempt)
                continue

            # any other error (wrong key, wrong model name) will not fix itself by retrying
            print(f"[{model}] error {response.status_code}: {response.text[:300]}")
            break

        print(f"Giving up on {model}, trying the next one...")

    return None


if __name__ == "__main__":
    answer = ask_gemini("Write a polite 30-word reply to someone asking about fees for a coaching batch.")
    if answer:
        print("AI says:", answer)
    else:
        print("All models failed. Try again in a few minutes.")