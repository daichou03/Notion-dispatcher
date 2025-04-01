from openai import OpenAI
from config import DEEPSEEK_API
from utils import parse_markdown_json

DEEPSEEK_CLIENT = OpenAI(api_key=DEEPSEEK_API, base_url="https://api.deepseek.com")
PROMPT_LENGTH_LIMIT = 8000


# Example of categories. Fetch from sheets_api.fetch_ai_categories
# categories = [
#     {
#         "label": "Swimming",
#         "description": "Related to swimming experiences and skills"
#     },
#     {
#         "label": "Doctor & Professional",
#         "description": "Academic, research, or professional topics"
#     },
#     {
#         "label": "Life & Experiences",
#         "description": "Travel, food, personal stories, etc."
#     },
#     {
#         "label": "Other",
#         "description": "Anything that does not fit other categories"
#     },
#     {
#         "label": "Food",
#         "description": "Information or review of a restaurant"
#     },
# ]


def build_batch_prompt(page_ids, page_texts, categories):
    """
    Build two strings: one for the system role and one for the user role.

    - page_ids: list of unique identifiers (matching the texts)
    - page_texts: list of texts that need analysis
    - categories: list of categories (label, description) for classification
    
    The AI is asked to return a JSON array of length = len(page_texts).
    Each element in the array corresponds to one (page_id, page_text) pair.
    The structure in each array element should be:
    {
      "page_id": "...",
      "category": "...",
      "tags": [...],
      "has_lexical_suggestion": false,
      "lexical_suggestion": ""
    }
    """

    # Create the category lines for the prompt
    category_lines = []
    for cat in categories:
        category_lines.append(f'• "{cat["label"]}": "{cat["description"]}"')
    categories_str = "\n".join(category_lines)

    # System content: overarching instructions
    system_content = (
        "You are an AI text analysis assistant. You will receive multiple short items in a single request. "
        "For each item, you must return ONLY valid JSON with the following fields: "
        "\"page_id\", \"category\", \"tags\", \"has_lexical_suggestion\", and \"lexical_suggestion\". "
        "No extra commentary, just the JSON. "
        "The final response must be a JSON array of objects, one object per input item."
    )

    # Build a multi-item user prompt
    # We'll list each item with an index, the page_id, and the text.
    items_str_list = []
    for i, (pid, text) in enumerate(zip(page_ids, page_texts), start=1):
        items_str_list.append(f"{i}) page_id: {pid}\n   text: {text}")

    items_block = "\n\n".join(items_str_list)

    # User content: instructions + the items + the required output structure
    user_content = f"""
Please analyze each of the following items and categorize them. Here are the requirements:

1. "page_id": The same page_id as provided in the input.
2. "category": Must be one of the known labels below (or "Other" if none match).
3. "tags": A list of short keywords describing the text.
4. "has_lexical_suggestion": A boolean, true if the text likely has spelling/grammar/transcription issues.
5. "lexical_suggestion": If has_lexical_suggestion is true, provide a corrected version in the original language; otherwise, leave it empty.

Here are the possible categories (label → description):
{categories_str}

Below are the items to analyze (page_id and text). Return your results as a JSON array of length {len(page_texts)}, 
where each element is a JSON object matching the format shown. 
The Nth object corresponds to the Nth item:

{items_block}

Your final response must be ONLY the JSON array in this structure (no extra text). 
For example, if we had 2 items, it would look like:

[
  {{
    "page_id": "...",
    "category": "...",
    "tags": ["...", "..."],
    "has_lexical_suggestion": false,
    "lexical_suggestion": ""
  }},
  {{
    "page_id": "...",
    "category": "...",
    "tags": ["...", "..."],
    "has_lexical_suggestion": false,
    "lexical_suggestion": ""
  }}
]
""".strip()

    return system_content, user_content


def send_to_deepseek_ai(prompt):
    """
    Form a JSON payload to the AI (DeepSeek) for:
      - category
      - custom tags
      - lexical suggestions
    Return the parsed results.
    
    Note: This is pseudo‐code for DeepSeek’s endpoint. 
    Replace 'DEEPSEEK_API_URL' with the actual URL and adapt the request/response as needed.
    """
    system_str, user_str = prompt
    if max(map(len, prompt)) > PROMPT_LENGTH_LIMIT:
        raise ValueError(f"Prompt length (either system or user) exceeds {PROMPT_LENGTH_LIMIT}")

    response = DEEPSEEK_CLIENT.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_str},
            {"role": "user", "content": user_str},
        ],
        stream=False
    )
    markdown_text = response.choices[0].message.content
    data = parse_markdown_json(markdown_text)
    return data