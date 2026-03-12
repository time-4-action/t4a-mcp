from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.product_service import get_price, ProductPrice, ProductPriceError


@mcp.tool()
@with_permission_check
def get_product_price(sku: str, pricelist_title: str = "RRP 2026") -> ProductPrice | ProductPriceError:
    """Look up pricing for a product by SKU from MetaKocka. Returns net price, VAT breakdown, and gross price.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU, then call this tool with the returned `code`.

    If the user asks about a specific pricelist (e.g. 'RRP 2025', 'RRP 2026'), pass it as pricelist_title.
    On failure, the response includes available_pricelists so you can inform the user which pricelists exist.

    Args:
        sku: Product SKU (always starts with 'P', e.g. 'P01250003085').
        pricelist_title: Name of the pricelist to use (default: 'RRP 2026').
    """
    require_permission("get_product_price")
    return get_price(sku, pricelist_title)
