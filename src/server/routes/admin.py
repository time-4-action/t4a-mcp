import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from src.ingestion.sources.products.cleaner import clean_products
from src.ingestion.sources.products.flattener import flatten_products
from src.ingestion.sources.products.formatter import create_embeddings_text
from src.ingestion.sources.products.loader import get_products
from src.vectorstore.updater import incremental_update

router = APIRouter(prefix="/admin")

_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


def _verify_api_key(x_api_key: str = Depends(_api_key_header)) -> None:
    expected = os.getenv("API_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


@router.post("/reindex-products", dependencies=[Depends(_verify_api_key)])
def reindex_products() -> dict:
    """Fetch all products from the upstream API and incrementally update the
    ChromaDB vector store — only new or changed products are re-embedded."""
    start = time.time()

    products = get_products()
    flat = flatten_products(products)
    clean = clean_products(flat)
    embedding_texts = create_embeddings_text(clean)

    stats = incremental_update(clean, embedding_texts)
    stats["duration_seconds"] = round(time.time() - start, 2)
    stats["total_products"] = len(clean)

    return stats
