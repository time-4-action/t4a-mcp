from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.delivery_service import (
    get_delivery_service_pricelists, PricelistResult, PricelistError,
)


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
