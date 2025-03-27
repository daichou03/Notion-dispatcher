import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_API_CRED
from dateutil import parser

NOTION_DISPATCHER_SPREADSHEET_NAME = "Notion Notes Nexus"
NOTION_DISPATCHER_WORKSHEET_NAME = "Record"

def retrieve_notion_worksheet():
    # Define the scope for accessing Google Sheets and Google Drive
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    # Provide the path to your credentials JSON file
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_API_CRED, scope)

    # Authorize the client
    client = gspread.authorize(creds)

    # Open the spreadsheet by its title (or you can use open_by_key or open_by_url)
    spreadsheet = client.open(NOTION_DISPATCHER_SPREADSHEET_NAME)

    # Retrieve the worksheet by its title (or use worksheet(index) for the index)
    worksheet = spreadsheet.worksheet(NOTION_DISPATCHER_WORKSHEET_NAME)

    # Now worksheet is a gspread Worksheet object that you can work with.
    return worksheet


def find_first_empty_id_row(worksheet, id_col):
    """
    Return the row number of the first empty cell in 'id_col' (below the header),
    or None if none is found (meaning the column is fully occupied or no blank).
    """
    # Get all values in the ID column
    # Note: col_values(1) returns ALL rows in that column (including row 1)
    id_column_values = worksheet.col_values(id_col)

    # Start from row 2, because row 1 is header
    for row_index in range(1, len(id_column_values)):
        # row_index is 0-based within the list, so the actual sheet row is row_index+1.
        # But we started from range(1,...), so actual row is row_index. We'll handle carefully below.
        actual_row = row_index + 1  # because the list is zero-based and we want 1-based sheet indexing
        cell_value = id_column_values[row_index]
        if not cell_value.strip():
            # Found an empty 'id' cell
            return actual_row

    return len(id_column_values) + 1  # No empty cell found in the existing range


def process_record(record, worksheet):
    """
    Process a single Notion page record and update a Google Sheet accordingly,
    but fill the first empty row (based on blank 'id' cell) rather than append.
    """

    # 1) Extract primary fields from the record
    page_id = record.get("id", "")
    raw_created_time = record.get("created_time", "")
    raw_last_edited_time = record.get("last_edited_time", "")

    # 2) Parse timestamps into Python datetime objects (if valid)
    created_dt = None
    last_edited_dt = None

    if raw_created_time:
        try:
            created_dt = parser.isoparse(raw_created_time)
        except Exception:
            created_dt = None

    if raw_last_edited_time:
        try:
            last_edited_dt = parser.isoparse(raw_last_edited_time)
        except Exception:
            last_edited_dt = None

    # 3) Extract content (e.g., from "Name" title property)
    title_parts = (
        record.get("properties", {})
              .get("Name", {})
              .get("title", [])
    )
    content = "".join(part.get("plain_text", "") for part in title_parts)

    # 4) Identify column indices
    headers = worksheet.row_values(1)
    try:
        id_col = headers.index("id") + 1
        created_time_col = headers.index("created_time") + 1
        last_edited_time_col = headers.index("last_edited_time") + 1
        content_col = headers.index("content") + 1
        to_analyse_col = headers.index("to_analyse") + 1
        ready_to_dispatch_col = headers.index("ready_to_dispatch") + 1
        dispatched_col = headers.index("dispatched") + 1
    except ValueError as e:
        raise Exception("One or more required headers are missing in the sheet.") from e

    # 5) Look for existing row by id
    try:
        cell = worksheet.find(page_id)
    except gspread.exceptions.CellNotFound:
        cell = None

    if cell is None:
        # 6) Not found in sheet -> fill a blank row
        empty_id_row = find_first_empty_id_row(worksheet, id_col)
        if empty_id_row > worksheet.row_count:
            # Exceeds number of existing rows, append
            worksheet.append_row([""] * len(headers))
        if created_dt:
            worksheet.update_cell(empty_id_row, created_time_col, created_dt.strftime("%Y-%m-%d %H:%M:%S"))
        if last_edited_dt:
            worksheet.update_cell(empty_id_row, last_edited_time_col, last_edited_dt.strftime("%Y-%m-%d %H:%M:%S"))
        worksheet.update_cell(empty_id_row, id_col, page_id)
        worksheet.update_cell(empty_id_row, content_col, content)
        worksheet.update_cell(empty_id_row, to_analyse_col, "TRUE")
        worksheet.update_cell(empty_id_row, ready_to_dispatch_col, "FALSE")
        worksheet.update_cell(empty_id_row, dispatched_col, "FALSE")
                
    else:
        # 7) Record found -> see if we need to update
        # TODO: test logic below
        row_number = cell.row
        row_data = worksheet.row_values(row_number)

        existing_last_edited_str = row_data[last_edited_time_col - 1]
        existing_ready_to_dispatch = row_data[ready_to_dispatch_col - 1]

        # Convert existing last_edited_time from sheet into datetime (if valid)
        existing_let = None
        if existing_last_edited_str:
            try:
                existing_let = parser.parse(existing_last_edited_str)
            except Exception:
                existing_let = None

        is_more_recent = False
        if last_edited_dt and (not existing_let or last_edited_dt > existing_let):
            is_more_recent = True

        # Only update if new record is more recent and not ready_to_dispatch
        if is_more_recent and existing_ready_to_dispatch != "TRUE":
            # Update last_edited_time, content, and to_analyse=TRUE
            if last_edited_dt:
                worksheet.update_cell(row_number, last_edited_time_col,
                                      last_edited_dt.strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(row_number, content_col, content)
            worksheet.update_cell(row_number, to_analyse_col, "TRUE")
