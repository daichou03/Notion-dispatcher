import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()  # this loads variables from .env into os.environ

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def query_notion_database(database_id):
    """
    Fetch all pages in the specified Notion database,
    handling pagination if there are more than 100 results.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    all_pages = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        
        # If we've already retrieved some pages, use next_cursor to get the next batch
        if next_cursor:
            payload["start_cursor"] = next_cursor

        # POST request to the Notion 'query' endpoint
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        # Append the new results to our list of pages
        all_pages.extend(data["results"])

        # Check if there's more data to retrieve
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    return all_pages


if __name__ == "__main__":
    # Fetch all pages from the database
    pages = query_notion_database(DATABASE_ID)

    # Example: Print each page's ID and Title property
    for page in pages:
        page_id = page["id"]
        
        # If your database has a 'Name' or 'Title' property:
        title_data = page["properties"].get("Name", {}).get("title", [])
        title_plain_text = title_data[0]["plain_text"] if title_data else "Untitled"
        
        print(f"Page ID: {page_id}")
        print(f"Title: {title_plain_text}")
        print("-----")
