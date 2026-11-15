import os
import requests
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {"chat_id": chat_id, "text": "Hello from your Telegram bot!, this is the first message sent from the bot."}

response = requests.post(url, json=payload, timeout=30)

print(response.status_code)
print(response.json())