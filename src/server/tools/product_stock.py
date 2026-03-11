from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.product_service import get_stock, ProductStock, ProductStockError


@mcp.tool()
@with_permission_check
def get_product_stock(sku: str, warehouse_id: str | None = None) -> ProductStock | ProductStockError:
    """Look up warehouse stock for a product by SKU. Returns available quantity, reservations, and location.

    If the user provides a SKU directly (always starts with 'P', e.g. 'P01250003085'), call this tool immediately.
    If the user provides a product name or description instead, first call `identify_product` to find the SKU, then call this tool with the returned `code`.

    By default checks stock in the configured warehouse. Pass `warehouse_id` to query a different warehouse.
    Use `get_warehouse_list_tool` to discover available warehouse IDs and their names.

    Args:
        sku:          Product SKU (always starts with 'P', e.g. 'P01250003085').
        warehouse_id: Optional MetaKocka warehouse mk_id to query instead of the default warehouse.
    """
    require_permission("get_product_stock")
    return get_stock(sku, warehouse_id=warehouse_id)
