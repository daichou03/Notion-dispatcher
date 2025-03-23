import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials


#.env format:
# GOOGLE_API_CRED = "./google-api-cred/********.json"

load_dotenv()  # this loads variables from .env into os.environ

GOOGLE_API_CRED = os.getenv("GOOGLE_API_CRED")   # Also put google api cred file there


# Define the scope for accessing Google Sheets and Google Drive
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# Provide the path to your credentials JSON file
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_API_CRED, scope)

# Authorize the client
client = gspread.authorize(creds)

# Open the spreadsheet by its title (or you can use open_by_key or open_by_url)
spreadsheet = client.open("Notion Notes Nexus")

# Retrieve the worksheet by its title (or use worksheet(index) for the index)
worksheet = spreadsheet.worksheet("Record")

# Now worksheet is a gspread Worksheet object that you can work with.
print("Worksheet retrieved:", worksheet.title)
