"""Module for preparing product data for embeddings."""

__all__ = ["create_embedding_text", "create_embeddings_text"]


def create_embedding_text(product):
    """Create embedding text for a single product.

    Args:
        product (dict): Product dictionary with product_name, descriptions.

    Returns:
        str: Formatted embedding text combining all product information.
    """
    parts = [
        f"Name: {product['product_name']}",
        f"Short Description: {product['short_description']}",
        f"Detailed Description: {product['detailed_description']}",
    ]
    return "\n".join(parts).strip()


def create_embeddings_text(products):
    """Create embedding text for all products.

    Args:
        products (list): List of product dictionaries.

    Returns:
        list: List of embedding text strings, one per product.
    """
    return [create_embedding_text(product) for product in products]