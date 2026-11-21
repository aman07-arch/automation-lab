import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load the .env that sits one folder above /scripts, and let it override anything stale
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

API_KEY = os.getenv("GEMINI_API_KEY")
RAW_MODELS = os.getenv("GEMINI_MODELS", "")
MODELS = [m.strip() for m in RAW_MODELS.split(",") if m.strip()]

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
                try:
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError, ValueError):
                    print(f"[{model}] unexpected response: {response.text[:300]}")
                    break  # move to the next model

            if response.status_code in RETRY_CODES:
                print(f"[{model}] try {attempt}: busy (status {response.status_code}), waiting...")
                time.sleep(5 * attempt)
                continue

            # 400/403/404 will not fix themselves by retrying
            print(f"[{model}] error {response.status_code}: {response.text[:200]}")
            break

    return None


if __name__ == "__main__":
    print("Reading .env from:", ENV_PATH)
    print("Models I will try:", MODELS)

    if not API_KEY:
        raise SystemExit("GEMINI_API_KEY is missing from .env")
    if not MODELS:
        raise SystemExit("GEMINI_MODELS is empty or missing in .env")

    answer = ask_gemini("Write a polite 30-word reply to someone asking about fees for a coaching batch.")
    if answer:
        print("AI says:", answer)
    else:
        print("All models in GEMINI_MODELS failed.")