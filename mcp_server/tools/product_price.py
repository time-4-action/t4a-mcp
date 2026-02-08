from mcp_server import mcp
from mcp_server.services.product_service import get_price, ProductPrice, ProductPriceError


@mcp.tool()
def get_product_price(sku: str) -> ProductPrice | ProductPriceError:
    """Look up pricing for a product by SKU. Returns net price, VAT breakdown, and gross price from the best-matching pricelist.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU, then call this tool with the returned `code`.

    Args:
        sku: Product SKU (always starts with 'P', e.g. 'P01250003085').
    """
    return get_price(sku)
