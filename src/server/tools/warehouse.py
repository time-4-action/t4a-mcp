from src.server import mcp
from src.server.permissions import require_permission
from src.server.services.warehouse_service import (
    get_warehouse_list, WarehouseListResult,
    get_warehouse_stock, WarehouseStockResult,
    WarehouseError,
)


@mcp.tool()
def get_warehouse_stock_tool(
    wh_id_list: str | None = None,
    product_code_list: str | None = None,
    product_mk_id_list: str | None = None,
    eshop_sync: bool = False,
    offset: int = 0,
    limit: int = 100,
) -> WarehouseStockResult | WarehouseError:
    """Query raw warehouse stock levels across all warehouses for multiple products.

    Use this for bulk stock queries or cross-warehouse stock analysis.
    For a single product's stock in the configured warehouse, use get_product_stock instead.

    Stock entries include amount, reserved_amount, free_amount (if reservations enabled),
    warehouse_id, microlocation, and unit.

    Args:
        wh_id_list:        Comma-separated warehouse mk_ids to filter by (e.g. "1600000067,1600000042").
                           Use get_warehouse_list_tool to discover warehouse IDs.
                           Omit to return stock from all warehouses.
        product_code_list: Comma-separated product codes/SKUs to filter by (e.g. "P01234,P05678").
        product_mk_id_list: Comma-separated product mk_ids to filter by.
        eshop_sync:        If True, only return products flagged for e-commerce sync.
        offset:            Pagination offset (default 0).
        limit:             Page size (default 100, max 1000).

    Returns:
        WarehouseStockResult with stock_list entries, or WarehouseError on failure.
    """
    require_permission("get_warehouse_stock")
    return get_warehouse_stock(
        wh_id_list=wh_id_list,
        product_code_list=product_code_list,
        product_mk_id_list=product_mk_id_list,
        eshop_sync=eshop_sync,
        offset=offset,
        limit=limit,
    )


@mcp.tool()
def get_warehouse_list_tool() -> WarehouseListResult | WarehouseError:
    """Fetch all warehouses configured in MetaKocka.

    Returns each warehouse's mark (identifier used in orders), name, address,
    type, and whether it is active or included in stock aggregates.

    Use the warehouse mark when filtering orders or stock by warehouse.

    Returns:
        WarehouseListResult with count and list of warehouses,
        or WarehouseError on failure.
    """
    require_permission("get_warehouse_list")
    return get_warehouse_list()
