from notion_api import *
from sheets_api import *
from ai_analysis import *
from dispatcher import *

# Flag: new & to_analyse
def notion_to_google_sheets():
    all_pages = query_notion_database()
    sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
    bulk_import_notion_page(all_pages, sheet_record)  # Warning: potentially many API calls

# Flag: to_analyse -> ready_to_dispatch
def google_sheets_to_ai():
    sheet_category = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_CATEGORY)
    sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
    categories = fetch_ai_categories(sheet_category)
    page_ids, page_texts = fetch_page_texts_to_analyse(sheet_record)
    prompt = build_batch_prompt(page_ids, page_texts, categories)  # Warning: potentially large number of tokens
    result_data = send_to_deepseek_ai(prompt)
    update_ai_classification_in_record(sheet_record, result_data)

# Flag: ready_to_dispatch -> dispatched
def google_sheets_to_dispatch():
    sheet_record = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
    rows = get_rows_to_dispatch(sheet_record)
    print(f"Found {len(rows)} rows to dispatch.")
    driver = init_browser()
    for row_idx, content, link in rows:
        print(f"→ Dispatching row {row_idx} …")
        if dispatch_note(driver, content, link):
            mark_dispatched(sheet_record, row_idx)
    print("Dispatch complete.")
    driver.quit()

# Flag: dispatched -> source_archived
def google_sheets_to_archive():
    sheet = retrieve_notion_worksheet(NOTION_DISPATCHER_WORKSHEET_NAME_RECORD)
    rows = get_rows_to_archive(sheet)
    print(f"Found {len(rows)} rows to archive in Notion.")
    for row_idx, record_id in rows:
        print(f"→ Archiving Notion record {record_id} (row {row_idx}) …")
        if remove_notion_record(record_id):
            mark_source_archived(sheet, row_idx)
    print("Archive pass complete.\n")
