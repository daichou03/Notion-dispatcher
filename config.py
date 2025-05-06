from dotenv import load_dotenv
import os


load_dotenv()  # this loads variables from .env into os.environ

## notion_api
NOTION_TOKEN = os.getenv("NOTION_TOKEN")  # NOTION_TOKEN = "ntn_**********************************************"
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  #DATABASE_ID = "********************************"

## sheets_api: where you put google api json file
GOOGLE_API_CRED = os.getenv("GOOGLE_API_CRED")  # GOOGLE_API_CRED = "./google-api-cred/********************************.json"

## deepseek_api
DEEPSEEK_API = os.getenv("DEEPSEEK_API")  # DEEPSEEK_API = "sk-********************************"

## dispatcher.api
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR")  # CHROME_USER_DATA_DIR = "C:/Users/****/AppData/Local/Google/Chrome/User Data"
CHROME_PROFILE = os.getenv("CHROME_PROFILE")  # CHROME_PROFILE = "Default"
CHROME_CANARY_LOCATION = os.getenv("CHROME_CANARY_LOCATION")  # CHROME_CANARY_LOCATION = "C:/Users/****/AppData/Local/Google/Chrome SxS/Application/chrome.exe"
FIREFOX_USER_DATA = os.getenv("FIREFOX_USER_DATA")  # FIREFOX_USER_DATA = os.getenv("C:/Users/****/AppData/Roaming/Mozilla/Firefox/Profiles/****")