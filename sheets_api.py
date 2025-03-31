import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_API_CRED
from dateutil import parser
from gspread.utils import rowcol_to_a1

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


def import_notion_page(page, worksheet):
    """
    Process a single Notion page record and update a Google Sheet accordingly,
    filling the first empty row if new, or updating the existing row if older.
    This version does minimal requests by updating the entire row at once.
    """

    # 1) Extract primary fields
    page_id = page.get("id", "")
    raw_created_time = page.get("created_time", "")
    raw_last_edited_time = page.get("last_edited_time", "")

    created_dt = None
    if raw_created_time:
        try:
            created_dt = parser.isoparse(raw_created_time)
        except:
            pass

    last_edited_dt = None
    if raw_last_edited_time:
        try:
            last_edited_dt = parser.isoparse(raw_last_edited_time)
        except:
            pass

    # 2) Extract content from Notion's "Name" property
    title_parts = (
        page.get("properties", {})
            .get("Name", {})
            .get("title", [])
    )
    content = "".join(part.get("plain_text", "") for part in title_parts)

    # 3) Identify columns by their header
    headers = worksheet.row_values(1)
    try:
        id_col = headers.index("id") + 1
        created_time_col = headers.index("created_time") + 1
        last_edited_time_col = headers.index("last_edited_time") + 1
        content_col = headers.index("content") + 1
        to_analyse_col = headers.index("to_analyse") + 1
        ready_to_dispatch_col = headers.index("ready_to_dispatch") + 1
        dispatched_col = headers.index("dispatched") + 1
    except ValueError:
        raise Exception("One or more required headers are missing in the sheet.")

    # 4) Search for existing ID in the sheet
    try:
        cell = worksheet.find(page_id)
    except gspread.exceptions.CellNotFound:
        cell = None

    if cell is None:
        # -----------------------------
        # NEW RECORD: find empty row
        # -----------------------------
        empty_id_row = find_first_empty_id_row(worksheet, id_col)

        # If row is beyond current sheet row_count, add a blank row
        if empty_id_row >= worksheet.row_count:
            worksheet.append_row([""] * len(headers))

        # Build one row of data
        new_row_values = [""] * len(headers)

        # Fill in columns as needed
        new_row_values[id_col - 1] = page_id
        if created_dt:
            new_row_values[created_time_col - 1] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        if last_edited_dt:
            new_row_values[last_edited_time_col - 1] = last_edited_dt.strftime("%Y-%m-%d %H:%M:%S")

        new_row_values[content_col - 1] = content
        new_row_values[to_analyse_col - 1] = True   # Mark for analysis
        new_row_values[ready_to_dispatch_col - 1] = False
        new_row_values[dispatched_col - 1] = False

        # We can do a single update for this entire row
        start_a1 = rowcol_to_a1(empty_id_row, 1)  # e.g. "A5"
        end_a1   = rowcol_to_a1(empty_id_row, len(headers))  # e.g. "G5"
        row_range = f"{start_a1}:{end_a1}"

        worksheet.update(row_range, [new_row_values])

    else:
        # -----------------------------
        # EXISTING RECORD: check update
        # -----------------------------
        row_number = cell.row
        row_data = worksheet.row_values(row_number)

        existing_last_edited_str = row_data[last_edited_time_col - 1]
        existing_ready_to_dispatch = row_data[ready_to_dispatch_col - 1]

        existing_let = None
        if existing_last_edited_str:
            try:
                existing_let = parser.parse(existing_last_edited_str)
            except:
                pass

        # Compare if new record is more recent
        is_more_recent = (
            last_edited_dt
            and (not existing_let or last_edited_dt > existing_let)
        )

        # Only update if more recent AND not flagged ready_to_dispatch
        if is_more_recent and existing_ready_to_dispatch != "TRUE":
            # Build a single row update
            current_row_values = worksheet.row_values(row_number)

            # Update the relevant columns in memory first
            if last_edited_dt:
                current_row_values[last_edited_time_col - 1] = last_edited_dt.strftime("%Y-%m-%d %H:%M:%S")
            current_row_values[content_col - 1] = content
            current_row_values[to_analyse_col - 1] = True

            # Now do a single update
            start_a1 = rowcol_to_a1(row_number, 1)  
            end_a1   = rowcol_to_a1(row_number, len(headers))
            row_range = f"{start_a1}:{end_a1}"

            worksheet.update(row_range, [current_row_values], value_input_option="USER_ENTERED")

# Assuming pages are in reverse order of date
def bulk_import_notion_page(pages, worksheet, interval=100):
    for page in pages[::-1]:
        import_notion_page(page, worksheet)
        time.sleep(interval)
