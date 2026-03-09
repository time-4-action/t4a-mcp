from src.server import mcp
from src.server.permissions import require_permission
from src.server.services.product_service import get_stock, ProductStock, ProductStockError


@mcp.tool()
def get_product_stock(sku: str) -> ProductStock | ProductStockError:
    """Look up warehouse stock for a product by SKU. Returns available quantity, reservations, and location.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU, then call this tool with the returned `code`.

    This checks stock in the configured warehouse only.

    Args:
        sku: Product SKU (always starts with 'P', e.g. 'P01250003085').
    """
    require_permission("get_product_stock")
    return get_stock(sku)
