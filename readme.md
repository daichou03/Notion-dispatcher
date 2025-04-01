### Read all casual notes from Notion
```python
from notion_api import *
all_pages = query_notion_database()
```

### Export all notes to Google Sheet
```python
from sheets_api import *
sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
bulk_import_notion_page(all_pages, sheet_record)  # Warning: potentially many API calls
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
prompt = build_batch_prompt(page_ids, page_texts, categories)  # Warning: potentially large number of tokens
result_data = send_to_deepseek_ai(prompt)
```

### Update AI results to Google Sheet
```python
update_ai_classification_in_record(sheet_record, result_data)
```
