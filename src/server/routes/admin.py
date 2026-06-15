import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from src.server.services.product_reindex import reindex_products as run_reindex_products

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
    return run_reindex_products()
