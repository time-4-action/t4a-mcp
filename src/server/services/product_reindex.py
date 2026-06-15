"""Shared product reindex logic.

Fetches all products from the upstream API and incrementally updates the
ChromaDB vector store — only new or changed products are re-embedded.

Used by both the `/admin/reindex-products` HTTP endpoint and the optional
cron-driven background scheduler (see `src/server/scheduler.py`).
"""

import time

from src.ingestion.sources.products.cleaner import clean_products
from src.ingestion.sources.products.flattener import flatten_products
from src.ingestion.sources.products.formatter import create_embeddings_text
from src.ingestion.sources.products.loader import get_products
from src.vectorstore.updater import incremental_update


def reindex_products() -> dict:
    """Run a full incremental product reindex and return stats."""
    start = time.time()

    products = get_products()
    flat = flatten_products(products)
    clean = clean_products(flat)
    embedding_texts = create_embeddings_text(clean)

    stats = incremental_update(clean, embedding_texts)
    stats["duration_seconds"] = round(time.time() - start, 2)
    stats["total_products"] = len(clean)

    return stats
