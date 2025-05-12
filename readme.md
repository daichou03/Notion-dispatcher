from main import *

### Copy all casual notes from Notion to Google Sheet
```python
notion_to_google_sheets()
```

### Retrieve notes and categories to analyse from Google Sheet, send notes to DeepSeek, update AI results to Google Sheet
```python
google_sheets_to_ai()
```

### Dispatch: Send notes to Milanote
```python
google_sheets_to_dispatch()
```

### Remove: Archive dispatched notes on Notion
```python
google_sheets_to_archive()
```

#### Outstanding issue
notion_to_google_sheets(): Wait infinitely when network poor
google_sheets_to_ai(): to split per prompt