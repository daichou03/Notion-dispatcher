import json
import re

def parse_markdown_json(markdown_text):
    """
    Given a string that likely includes a fenced code block (```json ... ```),
    extract just the JSON portion and parse it into a Python dict.
    
    Example input:
        ```json
        {
          "category": "Food",
          "tags": ["restaurant", "review"],
          "has_lexical_suggestion": false,
          "lexical_suggestion": ""
        }
        ```
    Returns:
        A Python dictionary with the parsed JSON data, or {} if parsing fails.
    """
    # 1) Remove any triple-backtick fences like ```json ... ```
    #    This regex will match the opening fences (```json or ```),
    #    as well as the closing triple backticks.
    #    The 's' (DOTALL) flag lets '.' match newlines. The 'i' flag for ignoring 'json' case.
    pattern = r"```[^\n]*\n([\s\S]*?)\n```"
    match = re.search(pattern, markdown_text, flags=re.IGNORECASE)
    
    if match:
        json_str = match.group(1).strip()
    else:
        # If we don't find fenced code, assume the entire text might be JSON.
        json_str = markdown_text.strip()
    
    # 2) Attempt to parse the extracted content as JSON.
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print("Warning: can't parse as JSON, possibly because the result is cut off. Return raw markdown_text instead.")
        data = markdown_text
    
    return data
