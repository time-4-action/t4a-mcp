"""MCP server that exposes product identification via vector similarity search."""

import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Resolve the chroma_db path relative to project root
CHROMA_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")

mcp = FastMCP("product-identifier", host="0.0.0.0", port=8000)

# Initialize once at module level so the vectorstore is reused across calls
_vectorstore = None


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        _vectorstore = Chroma(
            collection_name="products",
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings,
        )
    return _vectorstore


@mcp.tool()
def identify_product(query: str, n: int = 5) -> list[dict]:
    """Search the product vector store and return the top N matching products.

    Args:
        query: Free-text search string (e.g. product name, code, description).
        n: Number of results to return (default 5).

    Returns:
        List of matching products with name, code, ean, score, and content.
    """
    
    print("IP:", query)
    vectorstore = _get_vectorstore()
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=n)

    results = []
    for doc, score in docs_with_scores:
        results.append({
            "product_name": doc.metadata.get("product_name", ""),
            "code": doc.metadata.get("code", ""),
            "ean": doc.metadata.get("ean", ""),
            "score": round(float(score), 4),
            "content": doc.page_content,
        })
    return results


@mcp.tool()
def get_product_price(sku: str) -> dict:
    """Get the price for a product by its SKU code.

    Args:
        sku: The product SKU code.

    Returns:
        Product price in EUR including VAT.
    """
    print("PP:", sku)
    price = random.randint(5000, 8000)
    return {
        "sku": sku,
        "price": price,
        "currency": "EUR",
        "vat_included": True,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
