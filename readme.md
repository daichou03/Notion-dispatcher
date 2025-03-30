### Read all casual notes from Notion
```python
from notion_api import *
all_pages = query_notion_database()
```

### Directly send it to DeepSeek
```python
page_text = get_notion_page_text(all_pages[-1])  # Just the oldest note
from ai_analysis import *
prompt = build_prompt(page_text)
result_tuple = send_to_deepseek_ai(prompt)
```

### Import to Google Sheet
```python
from sheets_api import *
worksheet = retrieve_notion_worksheet()
bulk_import_notion_page(all_pages, worksheet)
```