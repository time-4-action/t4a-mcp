from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.delivery_service import (
    search_tracking_code, TrackingResult, TrackingError,
    get_delivery_service_pricelists, PricelistResult, PricelistError,
)


@mcp.tool()
@with_permission_check
def search_tracking_code_tool(
    tracking_code: str | None = None,
    sticker_code: str | None = None,
) -> TrackingResult | TrackingError:
    """Find a sales order by its delivery tracking code or sticker barcode.

    Provide exactly one of tracking_code or sticker_code.

    Args:
        tracking_code: Delivery carrier tracking number (or return tracking number).
        sticker_code:  Sticker barcode number (alternative to tracking_code).

    Returns:
        TrackingResult with mk_id, count_code, and tracking codes,
        or TrackingError if not found.
    """
    require_permission("search_tracking_code")
    return search_tracking_code(tracking_code=tracking_code, sticker_code=sticker_code)


@mcp.tool()
@with_permission_check
def get_delivery_service_pricelists_tool() -> PricelistResult | PricelistError:
    """Fetch all delivery service price lists configured in MetaKocka.

    Returns pricing tiers for each delivery type (e.g. GLS Slovenija, GLS Italy),
    including transport cost, COD cost, return cost, and package weight brackets.

    Returns:
        PricelistResult with count and list of price lists,
        or PricelistError on failure.
    """
    require_permission("get_delivery_service_pricelists")
    return get_delivery_service_pricelists()
