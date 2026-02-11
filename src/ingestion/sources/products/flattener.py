"""Module for flattening product data into a single-level structure."""

__all__ = ["flatten_products"]


def flatten_products(products):
    """Flatten products into a single-level structure with descriptions.

    For each parent product:
    - If it has child products, create an entry for each child using child's code/ean/name
      with parent's short and detailed descriptions
    - If no child products, use the parent itself

    Args:
        products (list): List of product dictionaries from the API.

    Returns:
        list: List of flattened products with structure:
            {
                "code": str,
                "ean": str,
                "product_name": str,
                "short_description": str,
                "detailed_description": str,
                "published": bool
            }
    """
    flattened = []

    for product in products:
        short_desc = product.get("short_description", "")
        detailed_desc = product.get("detailed_description", "")
        published = product.get("published", False)

        # If product has child products, flatten each child
        if product.get("child_products"):
            for child in product["child_products"]:
                flattened.append({
                    "code": child.get("code", ""),
                    "ean": child.get("ean_code", ""),
                    "product_name": child.get("product_name", ""),
                    "parent_name": product.get("product_name", ""),  # Pass parent name for filtering
                    "short_description": short_desc,
                    "detailed_description": detailed_desc,
                    "published": published
                })
        else:
            # No child products, use parent (parent_name is same as product_name)
            parent_name = product.get("product_name", "")
            flattened.append({
                "code": product.get("code", ""),
                "ean": product.get("ean_code", ""),
                "product_name": parent_name,
                "parent_name": parent_name,  # For consistency, parent_name = product_name when no children
                "short_description": short_desc,
                "detailed_description": detailed_desc,
                "published": published
            })

    return flattened
