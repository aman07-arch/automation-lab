import os
import gspread
from dotenv import load_dotenv

load_dotenv()

gc = gspread.service_account(filename=os.getenv("SERVICE_ACCOUNT_FILE"))
sheet = gc.open("Leads Test").sheet1

rows = sheet.get_all_records()
for row in rows:
    print(row["Name"], "|", row["Message"], "|", row["Status"])