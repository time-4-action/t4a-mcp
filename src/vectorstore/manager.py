import logging

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from src.config import CHROMA_HOST, CHROMA_PORT

logger = logging.getLogger(__name__)


def initialize_vectorstore() -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    chroma_client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
    )
    vs = Chroma(
        collection_name="products",
        client=chroma_client,
        embedding_function=embeddings,
    )

    if vs._collection.count() == 0:
        logger.info("ChromaDB is empty — running initial product indexing, this may take a few minutes...")
        _run_initial_indexing()
        logger.info("Initial product indexing complete.")

    return vs


def _run_initial_indexing() -> None:
    from src.ingestion.sources.products.cleaner import clean_products
    from src.ingestion.sources.products.flattener import flatten_products
    from src.ingestion.sources.products.formatter import create_embeddings_text
    from src.ingestion.sources.products.loader import get_products
    from src.vectorstore.updater import incremental_update

    products = get_products()
    flat = flatten_products(products)
    clean = clean_products(flat)
    texts = create_embeddings_text(clean)
    incremental_update(clean, texts)


vectorstore = initialize_vectorstore()
