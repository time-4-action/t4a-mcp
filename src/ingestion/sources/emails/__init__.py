"""Email data source."""

from src.ingestion.sources.emails.loader import get_emails
from src.ingestion.sources.emails.cleaner import clean_emails
from src.ingestion.sources.emails.formatter import create_embeddings_text

__all__ = ["get_emails", "clean_emails", "create_embeddings_text"]
