from pydantic import BaseModel, Field

from src.server import mcp
from src.server.permissions import require_permission, with_permission_check


class ProductURL(BaseModel):
    """Product search URL."""

    code: str = Field(description="Product code (SKU) used in the search.")
    url: str = Field(description="Direct URL to product search page.")


@mcp.tool()
@with_permission_check
def get_product_url(code: str) -> ProductURL:
    """Generate a web URL to search for a product on patrikinternational.com.

    Use this to provide users with a clickable link to view the product online.
    Takes the SKU code (starts with 'P'), not the count_code.

    Args:
        code: Product code/SKU (e.g. 'P01250002095'). Use the `code` field from `identify_product`.
    """
    require_permission("get_product_url")
    url = f"https://www.patrikinternational.com/en/shop/search/?query={code}"
    return ProductURL(code=code, url=url)
