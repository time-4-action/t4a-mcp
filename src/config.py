import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent

load_dotenv(ROOT_DIR / ".env")

CHROMA_DB_PATH = str(ROOT_DIR / "chroma_db")

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_MCP_AUDIENCE = os.getenv("AUTH0_MCP_AUDIENCE", "")

MK_SECRET_KEY = os.getenv("MK_SECRET_KEY", "")
MK_COMPANY_ID = os.getenv("MK_COMPANY_ID", "")
MK_BASE_URL = os.getenv("MK_BASE_URL", "")
MK_WAREHOUSE_ID = os.getenv("MK_WAREHOUSE_ID", "")

PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "https://api.time-4-action.com/api/export/product")

# Gmail IMAP Configuration
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_IMAP_SERVER = os.getenv("GMAIL_IMAP_SERVER", "imap.gmail.com")
GMAIL_IMAP_PORT = int(os.getenv("GMAIL_IMAP_PORT", "993"))

# Ordered list of pricelist titles by priority.
# get_price will return the first match found.
PRICELISTS = [
    "RRP 2026",
    "RRP 2025",
]

# ChromaDB HTTP service (used by both products and knowledge collections)
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
