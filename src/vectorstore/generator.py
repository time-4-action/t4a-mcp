"""Vector store generator for product embeddings using LangChain and ChromaDB.

This module handles:
1. Converting product data into LangChain Document objects
2. Generating embeddings using OpenAI
3. Storing embeddings in ChromaDB for similarity search
"""

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Any
from pydantic import SecretStr
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add parent directory to Python path so we can import from sibling modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


load_dotenv()

__all__ = ["generate_vectorstore", "create_documents"]


def create_documents(products: List[Dict[str, Any]], embedding_texts: List[str]) -> List[Document]:
    """Convert product data into LangChain Document objects.

    Documents are the core data structure in LangChain. Each document has:
    - page_content: The text that will be embedded (searchable content)
    - metadata: Additional information about the document (not embedded, but returned with results)

    Args:
        products: List of cleaned product dictionaries.
        embedding_texts: List of formatted text strings ready for embedding.

    Returns:
        List[Document]: LangChain documents with content and metadata.

    Example:
        products = [{'code': 'ABC123', 'product_name': 'Test Product', ...}]
        texts = ['Test Product Code: ABC123 ...']
        docs = create_documents(products, texts)
    """
    documents = []

    for product, text in zip(products, embedding_texts):
        # Create metadata - this info will be returned with search results
        # but won't be included in the embedding
        metadata = {
            "code": product.get("code", ""),
            "product_name": product.get("product_name", ""),
            "ean": product.get("ean", ""),

            # FIXME: GR20260207_1217
            # FIXME: categories, active & stock amount i think should be from MCP server
            # "categories": product.get("categories", []),
            # "active": product.get("active", True),
            # "stock_amount": product.get("stock_amount", 0),
        }

        # Create LangChain Document
        # page_content = the text that gets embedded and searched
        # metadata = additional info returned with search results
        doc = Document(
            page_content=text,
            metadata=metadata
        )
        documents.append(doc)

    return documents


def generate_vectorstore(
    products: List[Dict[str, Any]],
    embedding_texts: List[str],
    persist_directory: str = "./chroma_db",
    collection_name: str = "products",
    openai_api_key: str = ""
) -> Chroma:
    """Generate and persist a ChromaDB vectorstore from product data.

    This function:
    1. Creates LangChain Documents from your product data
    2. Initializes OpenAI embeddings (text-embedding-3-small model)
    3. Creates ChromaDB vectorstore and generates embeddings
    4. Persists the database to disk for future use

    Args:
        products: List of cleaned product dictionaries.
        embedding_texts: List of formatted text strings for embedding.
        persist_directory: Where to save the ChromaDB database.
        collection_name: Name for the ChromaDB collection.
        openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var).

    Returns:
        Chroma: The vectorstore instance (can be used immediately for search).

    Example:
        vectorstore = generate_vectorstore(products, texts)
        results = vectorstore.similarity_search("inflatable SUP", k=3)
    """
    print(f"📄 Creating {len(products)} documents...")
    documents = create_documents(products, embedding_texts)

    # Initialize OpenAI embeddings
    # text-embedding-3-small is cost-effective and performs well
    # You can also use "text-embedding-3-large" for better quality
    print("🔑 Initializing OpenAI embeddings...")
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=SecretStr(api_key)
    )

    # Create ChromaDB vectorstore
    # This will:
    # 1. Generate embeddings for all documents using OpenAI
    # 2. Store embeddings and documents in ChromaDB
    # 3. Persist to disk at persist_directory
    print(f"🔄 Generating embeddings and creating vectorstore...")
    print(f"📍 Persisting to: {persist_directory}")

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )

    print(f"✅ Vectorstore created successfully!")
    print(f"   - Collection: {collection_name}")
    print(f"   - Documents: {len(documents)}")
    print(f"   - Location: {persist_directory}")

    return vectorstore


def load_vectorstore(
    persist_directory: str = "./chroma_db",
    collection_name: str = "products",
    openai_api_key: str = "None"
) -> Chroma:
    """Load an existing ChromaDB vectorstore from disk.

    Use this to load a previously created vectorstore without regenerating embeddings.

    Args:
        persist_directory: Where the ChromaDB database is saved.
        collection_name: Name of the ChromaDB collection to load.
        openai_api_key: OpenAI API key (needed for new queries).

    Returns:
        Chroma: The loaded vectorstore instance.

    Example:
        vectorstore = load_vectorstore()
        results = vectorstore.similarity_search("windsurfing board", k=5)
    """
    print(f"📂 Loading vectorstore from {persist_directory}...")

    print("🔑 Initializing OpenAI embeddings...")
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=SecretStr(api_key)
    )

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory
    )

    print(f"✅ Vectorstore loaded successfully!")
    return vectorstore


if __name__ == "__main__":
    """
    Example usage when running this file directly.

    To use:
    1. Set your OPENAI_API_KEY environment variable
    2. Run: python embeddings/generator.py
    """
    # Import your ingestion pipeline
    from src.ingestion.sources.products.loader import get_products
    from src.ingestion.sources.products.flattener import flatten_products
    from src.ingestion.sources.products.cleaner import clean_products
    from src.ingestion.sources.products.formatter import create_embeddings_text

    print("🚀 Starting vectorstore generation...")
    print("-" * 50)

    # Run the full pipeline
    products = get_products()
    print(f"✓ Loaded {len(products)} products")

    flat = flatten_products(products)
    print(f"✓ Flattened to {len(flat)} items")

    clean = clean_products(flat)
    print(f"✓ Cleaned {len(clean)} items")

    embedding_texts = create_embeddings_text(clean)
    print(f"✓ Created {len(embedding_texts)} embedding texts")

    print("-" * 50)

    # Generate the vectorstore
    vectorstore = generate_vectorstore(
        products=clean,
        embedding_texts=embedding_texts,
        persist_directory="./chroma_db",
        collection_name="products"
    )

    print("-" * 50)
    print("🎉 Done! You can now use the vectorstore for similarity search.")
    print("\nExample query:")
    results = vectorstore.similarity_search("inflatable SUP board", k=3)
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. {doc.metadata['product_name']}")
        print(f"   Code: {doc.metadata['code']}")
        print(f"   Preview: {doc.page_content[:100]}...")
