import requests
import notion_api, sheets_api
from config import *

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
    pages = notion_api.query_notion_database(DATABASE_ID)

    # Example: Print each page's ID and Title property
    for page in pages:
        page_id = page["id"]
        
        # If your database has a 'Name' or 'Title' property:
        title_data = page["properties"].get("Name", {}).get("title", [])
        title_plain_text = title_data[0]["plain_text"] if title_data else "Untitled"
        
        print(f"Page ID: {page_id}")
        print(f"Title: {title_plain_text}")
        print("-----")