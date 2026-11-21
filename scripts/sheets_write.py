import os
import gspread
from dotenv import load_dotenv

load_dotenv()

gc = gspread.service_account(filename=os.getenv("SERVICE_ACCOUNT_FILE"))
sheet = gc.open("Leads Test").sheet1

# Row 1 is the header, so the first lead is row 2
# Column 3 = Reply, column 4 = Status
sheet.update_cell(2, 3, "Test reply from Python")
sheet.update_cell(2, 4, "replied")
print("Updated row 2")