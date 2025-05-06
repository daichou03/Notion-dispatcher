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

### Dispatch: Send notes to Milanote
```python
from sheets_api import *
sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
rows = get_rows_to_dispatch(sheet_record)
print(f"Found {len(rows)} rows to dispatch.")
from dispatcher import *
driver = init_browser()
for row_idx, content, link in rows:
    print(f"→ Dispatching row {row_idx} …")
    if dispatch_note(driver, content, link):
        mark_dispatched(sheet_record, row_idx)

print("Dispatch complete.")
driver.quit()
```

### Remove: Archive dispatched notes on Notion
```python
from sheets_api import *
sheet = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
rows = get_rows_to_archive(sheet)
print(f"Found {len(rows)} rows to archive in Notion.")
from notion_api import *
for row_idx, record_id in rows:
    print(f"→ Archiving Notion record {record_id} (row {row_idx}) …")
    if remove_notion_record(record_id):
        mark_source_archived(sheet, row_idx)
print("Archive pass complete.\n")
driver.quit()
```