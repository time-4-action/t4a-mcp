from src.server import mcp
from src.server.services.product_service import search_products


@mcp.tool()
def identify_product(query: str, n: int = 5) -> list[dict]:
    """Search the product vector store and return the top N matching products.

    Args:
        query: Free-text search string (e.g. product name, code, description).
        n: Number of results to return (default 5).

    Returns:
        List of matching products with name, code, ean, score, and content.
    """
    return search_products(query, n)
