from dotenv import load_dotenv
import os


load_dotenv()  # this loads variables from .env into os.environ

## notion_api
# NOTION_TOKEN = "ntn_**********************************************"
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
# DATABASE_ID = "********************************"
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


## sheets_api
GOOGLE_API_CRED = os.getenv("GOOGLE_API_CRED")   # Also put google api cred file there