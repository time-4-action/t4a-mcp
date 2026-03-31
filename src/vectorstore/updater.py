import os
from typing import Any, Dict, List

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from src.config import CHROMA_DB_PATH
from src.ingestion.sources.products.hasher import compute_hash, load_hash_index, save_hash_index
from src.vectorstore.generator import create_documents

HASH_INDEX_PATH = os.path.join(CHROMA_DB_PATH, "product_hashes.json")


def _doc_id(product: Dict[str, Any]) -> str:
    """Stable unique ID for a product document.

    Uses code::parent_name so that the same child product appearing under
    different parents gets a distinct ID while remaining stable across runs.
    """
    code = product.get("code", "")
    parent = product.get("parent_name", "")
    return f"{code}::{parent}"


def incremental_update(
    products: List[Dict[str, Any]],
    embedding_texts: List[str],
    persist_directory: str = CHROMA_DB_PATH,
    collection_name: str = "products",
    hash_index_path: str = HASH_INDEX_PATH,
) -> dict:
    """Update the ChromaDB collection with only new or changed products.

    Returns a dict with counts: added, updated, deleted, unchanged.
    """
    stored_hashes = load_hash_index(hash_index_path)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=SecretStr(api_key))
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )

    # On first run with an empty hash index, wipe any existing data so we can
    # rebuild with stable IDs (migrates from old UUID-based IDs).
    if not stored_hashes:
        existing = vectorstore._collection.get()
        if existing["ids"]:
            vectorstore._collection.delete(ids=existing["ids"])

    # Classify each product
    to_add: list = []
    to_update: list = []
    unchanged_count = 0
    current_ids: set = set()

    for product, text in zip(products, embedding_texts):
        doc_id = _doc_id(product)
        current_ids.add(doc_id)
        new_hash = compute_hash(text)

        if doc_id not in stored_hashes:
            to_add.append((product, text, doc_id, new_hash))
        elif stored_hashes[doc_id] != new_hash:
            to_update.append((product, text, doc_id, new_hash))
        else:
            unchanged_count += 1

    # Documents that were embedded before but no longer come from the API
    to_delete = [doc_id for doc_id in stored_hashes if doc_id not in current_ids]

    # Apply additions
    if to_add:
        add_products, add_texts, add_ids, add_hashes = zip(*to_add)
        docs = create_documents(list(add_products), list(add_texts))
        vectorstore.add_documents(docs, ids=list(add_ids))
        for doc_id, h in zip(add_ids, add_hashes):
            stored_hashes[doc_id] = h

    # Apply updates
    if to_update:
        upd_products, upd_texts, upd_ids, upd_hashes = zip(*to_update)
        docs = create_documents(list(upd_products), list(upd_texts))
        vectorstore.update_documents(ids=list(upd_ids), documents=docs)
        for doc_id, h in zip(upd_ids, upd_hashes):
            stored_hashes[doc_id] = h

    # Apply deletions
    if to_delete:
        vectorstore.delete(ids=to_delete)
        for doc_id in to_delete:
            del stored_hashes[doc_id]

    save_hash_index(stored_hashes, hash_index_path)

    return {
        "added": len(to_add),
        "updated": len(to_update),
        "deleted": len(to_delete),
        "unchanged": unchanged_count,
    }
