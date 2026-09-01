import os
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

EXCEL_FILE_ID = os.getenv("EXCEL_FILE_ID", "")
EXCEL_WORKSHEET_NAME = os.getenv("EXCEL_WORKSHEET_NAME", "Sheet1")
EXCEL_TABLE_NAME = os.getenv("EXCEL_TABLE_NAME", "Table1")

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]
