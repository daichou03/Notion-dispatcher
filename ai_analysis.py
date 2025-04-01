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


def build_batch_prompt(page_texts, categories):
    """
    Build two strings: one for the system role, one for the user role.
    - system_content: Overall instructions/context for the AI (how it should respond, what format, etc.)
    - user_content: The user prompt with the texts to be analyzed in batch and the list of categories.

    The AI is asked to return a JSON array, where each array element corresponds to one text in page_texts.
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
        "\"category\", \"tags\", \"has_lexical_suggestion\", and \"lexical_suggestion\". "
        "No extra commentary, just the JSON. "
        "The final response must be a JSON array of objects, one object per input text."
    )

    # Build a multi-item user prompt
    # We'll list each text with an index, then instruct the model to produce a corresponding JSON object.
    texts_str_list = []
    for i, text in enumerate(page_texts, start=1):
        texts_str_list.append(f"{i}) {text}")

    texts_block = "\n\n".join(texts_str_list)

    # User content: instructions + the texts + the required output structure
    user_content = f"""
Please analyze each of the following items and categorize them. Here are the requirements:

1. "category": Must be one of the known labels below (or "Other" if none match).
2. "tags": A list of short keywords describing the text.
3. "has_lexical_suggestion": A boolean, true if the text likely has spelling/grammar/transcription issues.
4. "lexical_suggestion": If has_lexical_suggestion is true, provide a corrected version in the original language; otherwise, leave it empty.

Here are the possible categories (label → description):
{categories_str}

Below are the texts to analyze (one per line). Return your results as a JSON array of length {len(page_texts)}, 
where each element is a JSON object matching the format shown. 
The Nth object corresponds to the Nth text:

{texts_block}

Your final response must be ONLY the JSON array in this structure (no extra text). 
For example, if we had 2 items, it would look like:

[
  {{
    "category": "...",
    "tags": ["...", "..."],
    "has_lexical_suggestion": false,
    "lexical_suggestion": ""
  }},
  {{
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