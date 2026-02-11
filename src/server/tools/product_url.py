from pydantic import BaseModel, Field

from src.server import mcp


class ProductURL(BaseModel):
    """Product search URL."""

    code: str = Field(description="Product code (SKU) used in the search.")
    url: str = Field(description="Direct URL to product search page.")


@mcp.tool()
def get_product_url(code: str) -> ProductURL:
    """Generate a web URL to search for a product on patrikinternational.com.

    Use this to provide users with a clickable link to view the product online.
    Takes the SKU code (starts with 'P'), not the count_code.

    Args:
        code: Product code/SKU (e.g. 'P01250002095'). Use the `code` field from `identify_product`.
    """
    url = f"https://www.patrikinternational.com/en/shop/search/?query={code}"
    return ProductURL(code=code, url=url)
