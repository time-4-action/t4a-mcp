"""Module for cleaning product data."""

import re
import html

__all__ = ["clean_html", "clean_products"]


def clean_html(text):
    """Remove HTML tags and decode entities, keeping text only.

    Args:
        text (str): Text that may contain HTML markup and entities.

    Returns:
        str: Cleaned text with HTML tags removed and whitespace normalized.
    """
    if not text:
        return ""

    # Decode HTML entities (e.g., &amp; -> &, &#123; -> {)
    text = html.unescape(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalize whitespace (collapse multiple spaces, remove leading/trailing)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_products(products):
    """Clean HTML from product descriptions and remove unpublished/closeout products.

    Args:
        products (list): List of flattened product dictionaries (from flattener).

    Returns:
        list: Products with cleaned short_description and detailed_description,
              excluding products where published=False or parent_name contains "CLOSE OUT".
    """
    cleaned = []

    for product in products:
        # Filter out products with published=False (defaults to True if field is missing)
        if not product.get("published", True):
            continue

        # Filter out closeout products - check parent product name for "CLOSE OUT"
        # The parent_name field is set during flattening (for children, it's the parent's name;
        # for products without children, it's the same as product_name)
        parent_name = product.get("parent_name", "")
        if "CLOSE OUT" in parent_name.upper():
            continue

        # Create a copy and clean the description fields
        cleaned_product = product.copy()
        cleaned_product["short_description"] = clean_html(product.get("short_description", ""))
        cleaned_product["detailed_description"] = clean_html(product.get("detailed_description", ""))
        cleaned.append(cleaned_product)

    return cleaned
