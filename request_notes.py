import os
import requests
import json
from dotenv import load_dotenv
import datetime
from dateutil import parser
import google_sheet


#.env format:
# NOTION_TOKEN = "ntn_**********************************************"
# DATABASE_ID = "********************************"

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


def process_record(record, worksheet):
    """
    Process a single Notion page record and update a Google Sheet accordingly.

    Parameters:
      record (dict): A Notion page record.
      worksheet: A gspread Worksheet object with the following headers in the first row:
                 "id", "created_time", "last_edited_time", "content", "to_analyse", "ready_to_dispatch".
    
    Behavior:
      - If the record's id does not exist in the sheet, a new row is appended with:
          id, created_time, last_edited_time, content from record,
          "to_analyse" set to 1, and ready_to_dispatch left blank.
      - If the record's id exists and its last_edited_time is newer than the one stored AND
        ready_to_dispatch is not 1, the row is updated with the new last_edited_time and content,
        and the to_analyse flag is set to 1.
      - Otherwise, no changes are made.
    """

    # Extract necessary values from the record
    page_id = record.get("id")
    created_time = record.get("created_time")
    last_edited_time = record.get("last_edited_time")
    
    # Extract content from the "Name" property (concatenate all text segments if necessary)
    title_parts = record.get("properties", {}).get("Name", {}).get("title", [])
    content = "".join([part.get("plain_text", "") for part in title_parts])

    # Retrieve header row to identify column indices (assuming headers are in row 1)
    headers = worksheet.row_values(1)
    try:
        id_col = headers.index("id") + 1
        created_time_col = headers.index("created_time") + 1
        last_edited_time_col = headers.index("last_edited_time") + 1
        content_col = headers.index("content") + 1
        to_analyse_col = headers.index("to_analyse") + 1
        ready_to_dispatch_col = headers.index("ready_to_dispatch") + 1
    except ValueError as e:
        raise Exception("One or more required headers are missing in the sheet.") from e

    # Search for the record by id in the sheet
    try:
        cell = worksheet.find(page_id)
    except Exception:
        cell = None

    if cell is None:
        # Record not found: append a new row
        new_row = [""] * len(headers)
        new_row[id_col - 1] = page_id
        new_row[created_time_col - 1] = created_time
        new_row[last_edited_time_col - 1] = last_edited_time
        new_row[content_col - 1] = content
        new_row[to_analyse_col - 1] = "1"  # flag for analysis
        new_row[ready_to_dispatch_col - 1] = ""  # not yet ready to dispatch
        worksheet.append_row(new_row)
    else:
        # Record found: check if an update is needed
        row_number = cell.row
        row_data = worksheet.row_values(row_number)
        
        # Retrieve the stored last_edited_time and ready_to_dispatch flag
        existing_last_edited_time = row_data[last_edited_time_col - 1]
        existing_ready_to_dispatch = row_data[ready_to_dispatch_col - 1]
        
        # Convert timestamp strings to datetime objects for comparison
        try:
            new_let = parser.isoparse(last_edited_time)
        except Exception as e:
            raise Exception("Invalid last_edited_time format in the new record.") from e
        
        try:
            existing_let = parser.isoparse(existing_last_edited_time) if existing_last_edited_time else None
        except Exception as e:
            existing_let = None
        
        # Update only if the new record is more recent and the record is not flagged as ready to dispatch
        if (existing_let is None or new_let > existing_let) and existing_ready_to_dispatch != "1":
            worksheet.update_cell(row_number, last_edited_time_col, last_edited_time)
            worksheet.update_cell(row_number, content_col, content)
            worksheet.update_cell(row_number, to_analyse_col, "1")
    return


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


# To fetch from google sheets
CATEGORIES = [
    {
        "label": "Swimming",
        "description": "Related to swimming experiences and skills"
    },
    {
        "label": "Doctor & Professional",
        "description": "Academic, research, or professional topics"
    },
    {
        "label": "Life & Experiences",
        "description": "Travel, food, personal stories, etc."
    },
    {
        "label": "Other",
        "description": "Anything that does not fit other categories"
    },
    {
        "label": "Food",
        "description": "Information or review of a restaurant"
    },
]


def build_prompt(page_text):
    """
Build a single prompt string instructing the AI to produce
a JSON with category_label, category_description, tags, 
has_lexical_suggestion, and lexical_suggestion.
    """
    # Create a textual list of categories + descriptions for the AI to reference
    category_lines = []
    for cat in CATEGORIES:
        category_lines.append(f'• "{cat["label"]}": "{cat["description"]}"')
    categories_str = "\n".join(category_lines)

    # We’ll instruct the AI to choose the label that best fits,
    # then return that label and description in the output.
    # We also want tags, lexical suggestions, etc.
    prompt = f"""
You are an AI text analysis assistant. Your job is to analyze the text and produce a JSON with:
1. "category": Must be one of the known labels below.
2. "tags": an array/list of short keywords describing the text.
3. "has_lexical_suggestion": a boolean, true if the text likely has spelling/grammar/transcription issues.
4. "lexical_suggestion": if has_lexical_suggestion is true, provide a corrected version in the original language; otherwise, leave it empty.

Here are the possible categories (label → description):
{categories_str}

Now analyze this text:
{page_text}

Return ONLY valid JSON. Follow this format exactly:
{{
  "category": "...",
  "tags": ["...", "..."],
  "has_lexical_suggestion": false,
  "lexical_suggestion": ""
}}
"""
    return prompt.strip()


def send_to_deepseek_ai(page_text):
    """
    Form a JSON payload to the AI (DeepSeek) for:
      - category
      - custom tags
      - lexical suggestions
    Return the parsed results.
    
    Note: This is pseudo‐code for DeepSeek’s endpoint. 
    Replace 'DEEPSEEK_API_URL' with the actual URL and adapt the request/response as needed.
    """

    # Construct the request payload
    payload = {
        "text": page_text,
        "categories": CATEGORIES  # The AI can use these as reference for classification
    }

    # Make the POST request to DeepSeek (or your AI service)
    DEEPSEEK_API_URL = "https://api.deepseek.ai/classify"  # example placeholder
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers)
    # Example response structure (adapt to your actual AI’s output)
    # {
    #   "category": "Swimming",
    #   "tags": ["food", "cost performance"],
    #   "has_lexical_suggestion": true,
    #   "lexical_suggestion": "食物：杨国福麻辣烫：评价性价比不佳"
    # }
    data = response.json()

    # Parse fields; default if missing
    category = data.get("category", "Other")
    tags = data.get("tags", [])
    has_lexical_suggestion = data.get("has_lexical_suggestion", False)
    lexical_suggestion = data.get("lexical_suggestion", "")

    return category, tags, has_lexical_suggestion, lexical_suggestion


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
