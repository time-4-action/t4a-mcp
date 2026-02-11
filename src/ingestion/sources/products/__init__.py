"""Product data source - legacy wrapper functions."""

from src.ingestion.sources.products.loader import get_products
from src.ingestion.sources.products.cleaner import clean_products
from src.ingestion.sources.products.formatter import create_embeddings_text
from src.ingestion.sources.products.flattener import flatten_products

__all__ = ["get_products", "clean_products", "create_embeddings_text", "flatten_products"]
