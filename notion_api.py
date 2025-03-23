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


import gspread
from dateutil import parser
from datetime import datetime

def find_first_empty_id_row(worksheet, id_col):
    """
    Return the row number of the first empty cell in 'id_col' (below the header),
    or None if none is found (meaning the column is fully occupied or no blank).
    """
    # Get all values in the ID column
    # Note: col_values(1) returns ALL rows in that column (including row 1)
    id_column_values = worksheet.col_values(id_col)

    # Start from row 2, because row 1 is header
    for row_index in range(1, len(id_column_values)):
        # row_index is 0-based within the list, so the actual sheet row is row_index+1.
        # But we started from range(1,...), so actual row is row_index. We'll handle carefully below.
        actual_row = row_index + 1  # because the list is zero-based and we want 1-based sheet indexing
        cell_value = id_column_values[row_index]
        if not cell_value.strip():
            # Found an empty 'id' cell
            return actual_row

    return None  # No empty cell found in the existing range


def process_record(record, worksheet):
    """
    Process a single Notion page record and update a Google Sheet accordingly,
    but fill the first empty row (based on blank 'id' cell) rather than append.
    """

    # 1) Extract primary fields from the record
    page_id = record.get("id", "")
    raw_created_time = record.get("created_time", "")
    raw_last_edited_time = record.get("last_edited_time", "")

    # 2) Parse timestamps into Python datetime objects (if valid)
    created_dt = None
    last_edited_dt = None

    if raw_created_time:
        try:
            created_dt = parser.isoparse(raw_created_time)
        except Exception:
            created_dt = None

    if raw_last_edited_time:
        try:
            last_edited_dt = parser.isoparse(raw_last_edited_time)
        except Exception:
            last_edited_dt = None

    # 3) Extract content (e.g., from "Name" title property)
    title_parts = (
        record.get("properties", {})
              .get("Name", {})
              .get("title", [])
    )
    content = "".join(part.get("plain_text", "") for part in title_parts)

    # 4) Identify column indices
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

    # (Optional) Check if there's a 'dispatched' column
    try:
        dispatched_col = headers.index("dispatched") + 1
    except ValueError:
        dispatched_col = None

    # 5) Look for existing row by id
    try:
        cell = worksheet.find(page_id)
    except gspread.exceptions.CellNotFound:
        cell = None

    if cell is None:
        # 6) Not found in sheet -> fill the first empty 'id' cell row or append if none
        empty_id_row = find_first_empty_id_row(worksheet, id_col)
        if empty_id_row is None:
            # If no empty ID cell found, fallback to appending
            empty_id_row = worksheet.row_count + 1  # or just use append_row() below

            new_row_data = [""] * len(headers)
            new_row_data[id_col - 1] = page_id
            if created_dt:
                new_row_data[created_time_col - 1] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
            if last_edited_dt:
                new_row_data[last_edited_time_col - 1] = last_edited_dt.strftime("%Y-%m-%d %H:%M:%S")
            new_row_data[content_col - 1] = content
            # use "TRUE"/"FALSE" for checkbox columns
            new_row_data[to_analyse_col - 1] = "TRUE"
            new_row_data[ready_to_dispatch_col - 1] = "FALSE"
            if dispatched_col:
                new_row_data[dispatched_col - 1] = "FALSE"

            worksheet.append_row(new_row_data)
        else:
            # We found a blank row for 'id', so we fill that row
            if created_dt:
                worksheet.update_cell(empty_id_row, created_time_col, created_dt.strftime("%Y-%m-%d %H:%M:%S"))
            if last_edited_dt:
                worksheet.update_cell(empty_id_row, last_edited_time_col, last_edited_dt.strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(empty_id_row, id_col, page_id)
            worksheet.update_cell(empty_id_row, content_col, content)
            worksheet.update_cell(empty_id_row, to_analyse_col, "TRUE")
            worksheet.update_cell(empty_id_row, ready_to_dispatch_col, "FALSE")
            if dispatched_col:
                worksheet.update_cell(empty_id_row, dispatched_col, "FALSE")

    else:
        # 7) Record found -> see if we need to update
        row_number = cell.row
        row_data = worksheet.row_values(row_number)

        existing_last_edited_str = row_data[last_edited_time_col - 1]
        existing_ready_to_dispatch = row_data[ready_to_dispatch_col - 1]

        # Convert existing last_edited_time from sheet into datetime (if valid)
        existing_let = None
        if existing_last_edited_str:
            try:
                existing_let = parser.parse(existing_last_edited_str)
            except Exception:
                existing_let = None

        is_more_recent = False
        if last_edited_dt and (not existing_let or last_edited_dt > existing_let):
            is_more_recent = True

        # Only update if new record is more recent and not ready_to_dispatch
        if is_more_recent and existing_ready_to_dispatch != "TRUE":
            # Update last_edited_time, content, and to_analyse=TRUE
            if last_edited_dt:
                worksheet.update_cell(row_number, last_edited_time_col,
                                      last_edited_dt.strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(row_number, content_col, content)
            worksheet.update_cell(row_number, to_analyse_col, "TRUE")


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
