import os
import time
from pathlib import Path

import gspread
import requests
from dotenv import load_dotenv

# ---------- Settings ----------
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_DIR / ".env", override=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()]
KEY_PATH = PROJECT_DIR / os.getenv("SERVICE_ACCOUNT_FILE", "secrets/service_account.json")

SHEET_NAME = "Leads Test"
RETRY_CODES = (429, 500, 503, 504)  # temporary problems worth retrying

# Sheet columns (1 = first column)
REPLY_COL = 3
STATUS_COL = 4


# ---------- Gemini ----------
def ask_gemini(message):
    """Returns the AI reply as text, or None if every model failed."""
    prompt = (
        "You are a friendly assistant for a coaching institute. "
        "Write a short, polite reply (maximum 50 words) to this inquiry: "
        f"{message}\n"
        "If you are unsure about details, say the team will confirm shortly. End your message with STOP to unsubscribe"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}

    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        for attempt in range(1, 4):  # up to 3 tries per model
            try:
                response = requests.post(url, headers=headers, json=body, timeout=60)
            except requests.exceptions.RequestException as error:
                print(f"  [{model}] try {attempt}: network problem ({type(error).__name__})")
                time.sleep(5 * attempt)
                continue

            if response.status_code == 200:
                try:
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError, ValueError):
                    print(f"  [{model}] unexpected response: {response.text[:200]}")
                    break  # go to the next model

            if response.status_code in RETRY_CODES:
                print(f"  [{model}] try {attempt}: busy (status {response.status_code}), waiting...")
                time.sleep(5 * attempt)
                continue

            print(f"  [{model}] error {response.status_code}: {response.text[:200]}")
            break  # 400/403/404 will not fix themselves by retrying

    return None
def classify(message):
        """Returns the AI reply as text, or None if every model failed."""
        prompt = (
            "You are a friendly assistant for a coaching institute. "
            "Classify this inquiry into one of these categories: 'Location', 'Timing', 'Fees', 'other'. "
            f"{message}\n"
            "Answer with only one word"
        )
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    
        for model in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
            for attempt in range(1, 4):  # up to 3 tries per model
                try:
                    response = requests.post(url, headers=headers, json=body, timeout=60)
                except requests.exceptions.RequestException as error:
                    print(f"  [{model}] try {attempt}: network problem ({type(error).__name__})")
                    time.sleep(5 * attempt)
                    continue
    
                if response.status_code == 200:
                    try:
                        data = response.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except (KeyError, IndexError, ValueError):
                        print(f"  [{model}] unexpected response: {response.text[:200]}")
                        break  # go to the next model
    
                if response.status_code in RETRY_CODES:
                    print(f"  [{model}] try {attempt}: busy (status {response.status_code}), waiting...")
                    time.sleep(5 * attempt)
                    continue
    
                print(f"  [{model}] error {response.status_code}: {response.text[:200]}")
                break  # 400/403/404 will not fix themselves by retrying
    
        return None



# ---------- Telegram ----------
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=30)
    except requests.exceptions.RequestException as error:
        print("  Telegram alert failed:", type(error).__name__)


# ---------- Main program ----------
def main():
    # 1. Check that settings exist before doing anything
    problems = []
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        problems.append("Telegram token or chat ID missing in .env")
    if not GEMINI_API_KEY:
        problems.append("GEMINI_API_KEY missing in .env")
    if not MODELS:
        problems.append("GEMINI_MODELS missing or empty in .env")
    if not KEY_PATH.exists():
        problems.append(f"Service account file not found at {KEY_PATH}")
    if problems:
        raise SystemExit("Fix these first:\n- " + "\n- ".join(problems))

    print("Models I will try:", MODELS)

    # 2. Open the sheet
    gc = gspread.service_account(filename=str(KEY_PATH))
    sheet = gc.open(SHEET_NAME).sheet1
    rows = sheet.get_all_records()
    print(f"Found {len(rows)} rows in the sheet.")

    done = 0
    failed = 0

    # 3. Go through the rows (row 1 is the header, so data starts at row 2)
    for row_number, row in enumerate(rows, start=2):
        name = row.get("Name", "")
        message = str(row.get("Message", "")).strip()
        status = str(row.get("Status", "")).strip().lower()
        category = str(row.get("Category", "")).strip().lower()

        if status != "new":
            continue  # already handled, skip it
        if not message:
            print(f"Row {row_number} ({name}): empty message, skipping.")
            continue

        print(f"Processing row {row_number}: {name}")
        reply = ask_gemini(message)

        if reply is None:
            failed += 1
            print(f"  Could not get a reply for {name}. Leaving it as 'new' for the next run.")
            send_telegram(f"ERROR: no AI reply for {name}. Will retry on the next run.")
            continue

        sheet.update_cell(row_number, REPLY_COL, reply)
        sheet.update_cell(row_number, STATUS_COL, "replied")
        sheet.update_cell(row_number, 5, classify(message))
        send_telegram(f"Replied to {name}")
        done += 1
        print(f"  Done: {name}")
        time.sleep(2)  # small pause so we don't hit rate limits

    print(f"Finished. Replied: {done}, failed: {failed}")


if __name__ == "__main__":
    main()