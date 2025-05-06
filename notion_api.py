import requests
from config import NOTION_TOKEN, NOTION_DATABASE_ID
from notion_client import Client
from notion_client.errors import APIResponseError

notion = Client(auth=NOTION_TOKEN)

def query_notion_database():
    """
    Fetch all pages in the specified Notion database,
    handling pagination if there are more than 100 results.
    """
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
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


def get_notion_page_text(page_obj):
    """
    Extract textual content from a Notion page object.
    In this example, we read from the 'Name' property (which is a 'title' type).
    Adapt if your notes are stored differently.
    """
    # Safely navigate the page's 'properties' dictionary
    title_prop = page_obj["properties"].get("Name", {})
    title_array = title_prop.get("title", [])
    # If there's at least one text block in the 'title' array
    if title_array:
        return title_array[0]["plain_text"]
    return ""

def remove_notion_record(record_id: str) -> bool:
    """
    Archives a Notion page by its ID.
    """
    try:
        # The pages.update endpoint supports an `archived` flag
        notion.pages.update(page_id=record_id, archived=True)
        return True
    except APIResponseError as e:
        print(f"[NotionAPI] Failed to archive {record_id}: {e}")
        return False

