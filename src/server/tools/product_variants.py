from src.server import mcp
from src.server.permissions import require_permission
from src.server.services.product_service import get_variants, ProductVariants, ProductVariantsError


@mcp.tool()
def get_product_variants(sku: str) -> ProductVariants | ProductVariantsError:
    """Get product variants and detailed descriptions. Returns parent product info with all variant SKUs, EANs, and names.

    Use this to find all sizes/colors/versions of a product or to get detailed descriptions.

    Args:
        sku: Product SKU code (starts with 'P', e.g. 'P03200001092').
    """
    require_permission("get_product_variants")
    return get_variants(sku)
