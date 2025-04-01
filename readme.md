### Read all casual notes from Notion
```python
from notion_api import *
all_pages = query_notion_database()
```

### Export all notes to Google Sheet
```python
from sheets_api import *
sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
bulk_import_notion_page(all_pages, sheet_record)  # Requires many API calls
```

### Retrieve notes and categories to analyse from Google Sheet
```python
from sheets_api import *
sheet_category = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_CATEGORY)
sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
categories = fetch_ai_categories(sheet_category)
page_ids, page_texts = fetch_page_texts_to_analyse(sheet_record)
```

### Send notes to DeepSeek
```python
from ai_analysis import *
prompt = build_batch_prompt(page_ids[:5], page_texts[:5], categories)
result_data = send_to_deepseek_ai(prompt)
```