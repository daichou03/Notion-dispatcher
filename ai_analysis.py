from openai import OpenAI
from config import DEEPSEEK_API
from utils import parse_markdown_json

DEEPSEEK_CLIENT = OpenAI(api_key=DEEPSEEK_API, base_url="https://api.deepseek.com")


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


def build_prompt(page_text, categories):
    """
    Build two strings: one for the system role, one for the user role.
    - system_content: Overall instructions/context for the AI (how it should respond, what format, etc.)
    - user_content: The user prompt with the text to be analyzed and the list of categories.
    """
    # Example categories list:
    # CATEGORIES = [
    #     {"label": "Swimming", "description": "All about swimming"},
    #     {"label": "Doctor & Professional", "description": "Academic or work-related"},
    #     ...
    # ]
    
    category_lines = []
    for cat in categories:
        category_lines.append(f'• "{cat["label"]}": "{cat["description"]}"')
    categories_str = "\n".join(category_lines)
    
    # System content: High-level instructions for the model
    system_content = (
        "You are an AI text analysis assistant. "
        "You will receive some text and must return ONLY valid JSON with the following fields: "
        "\"category\", \"tags\", \"has_lexical_suggestion\", and \"lexical_suggestion\". "
        "You should respond concisely without extra commentary."
    )
    
    # User content: Actual prompt to classify/correct the text
    # (includes categories, instructions, and the text to be analyzed).
    user_content = f"""
Please analyze the following text and categorize it. Here are the requirements:

1. "category": Must be one of the known labels below (or "Other" if none match).
2. "tags": A list of short keywords describing the text.
3. "has_lexical_suggestion": A boolean, true if the text likely has spelling/grammar/transcription issues.
4. "lexical_suggestion": If has_lexical_suggestion is true, provide a corrected version in the original language; otherwise, leave it empty.

Here are the possible categories (label → description):
{categories_str}

Text to analyze:
{page_text}

Return ONLY valid JSON. Follow this exact JSON structure:
{{
  "category": "...",
  "tags": ["...", "..."],
  "has_lexical_suggestion": false,
  "lexical_suggestion": ""
}}
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

    # Parse fields; default if missing
    category = data.get("category", "Other")
    tags = data.get("tags", [])
    has_lexical_suggestion = data.get("has_lexical_suggestion", False)
    lexical_suggestion = data.get("lexical_suggestion", "")

    return category, tags, has_lexical_suggestion, lexical_suggestion