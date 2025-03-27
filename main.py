import requests
import notion_api, sheets_api, ai_analysis
from config import *


if __name__ == "__main__":
    # Fetch all pages from the database
    pages = notion_api.query_notion_database()

    # Example: Print each page's ID and Title property
    for page in pages:
        page_id = page["id"]
        
        # If your database has a 'Name' or 'Title' property:
        title_data = page["properties"].get("Name", {}).get("title", [])
        title_plain_text = title_data[0]["plain_text"] if title_data else "Untitled"
        
        print(f"Page ID: {page_id}")
        print(f"Title: {title_plain_text}")
        print("-----")