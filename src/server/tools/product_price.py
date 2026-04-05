from src.server import mcp
from src.server.permissions import require_permission, with_permission_check, has_permission, get_current_permissions
from src.server.services.product_service import get_price, ProductPrice, ProductPriceError, DEFAULT_PRICELIST


@mcp.tool()
@with_permission_check
def get_product_price(sku: str, pricelist_title: str = DEFAULT_PRICELIST) -> ProductPrice | ProductPriceError:
    """Look up pricing for a product by SKU from MetaKocka. Returns net price, VAT breakdown, and gross price.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU, then call this tool with the returned `code`.

    The default pricelist is used unless the user explicitly asks for a different one AND has the required permission.
    If requesting a non-default pricelist fails due to permissions, use the default pricelist instead.

    Args:
        sku: Product SKU (always starts with 'P', e.g. 'P01250003085').
        pricelist_title: Name of the pricelist to use (default: current default pricelist).
    """
    require_permission("get_product_price")
    if pricelist_title != DEFAULT_PRICELIST and not has_permission(get_current_permissions(), ["products:pricelists:read"]):
        raise PermissionError(
            f"Forbidden: accessing pricelist '{pricelist_title}' requires 'products:pricelists:read' permission. "
            f"You can only access the default pricelist ('{DEFAULT_PRICELIST}')."
        )
    return get_price(sku, pricelist_title)
