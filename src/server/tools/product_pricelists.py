from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.product_service import (
    get_pricelists, get_all_pricelist_titles,
    ProductPricelists, ProductPricelistsError,
)


@mcp.tool()
@with_permission_check
def get_product_pricelists(sku: str) -> ProductPricelists | ProductPricelistsError:
    """List all available pricelists and their prices for a product from MetaKocka.

    Use this when the user asks which pricelists exist for a product, wants to compare
    prices across pricelists, or when `get_product_price` returns an error with missing pricelist.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU.

    Args:
        sku: Product SKU (always starts with 'P', e.g. 'P01250003085').
    """
    require_permission("get_product_pricelists")
    return get_pricelists(sku)


@mcp.tool()
@with_permission_check
def list_pricelists() -> list[str] | ProductPricelistsError:
    """List all pricelist names that exist in MetaKocka (not product-specific).

    Use this when the user asks what pricelists are available, which pricelists exist,
    or before calling get_product_price with a specific pricelist_title.

    MetaKocka has no dedicated endpoint for this, so a small sample of products is
    fetched internally to discover all unique pricelist titles.
    """
    require_permission("list_pricelists")
    return get_all_pricelist_titles()
