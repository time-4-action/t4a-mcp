from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.partner_service import (
    get_partner, PartnerResult, PartnerError,
)


@mcp.tool()
@with_permission_check
def get_partner_tool(
    partner_id: str | None = None,
    partner_name: str | None = None,
    partner_tax_number: str | None = None,
    partner_email: str | None = None,
    partner_phone_number: str | None = None,
    show_partner_discount: bool = False,
) -> PartnerResult | PartnerError:
    """Search for MetaKocka partners (customers/suppliers) by one or more fields.

    Provide at least one search field. Results include contact details and delivery addresses.

    Args:
        partner_id:           MetaKocka internal partner ID (mk_id).
        partner_name:         Partial or full partner name (case-insensitive search).
        partner_tax_number:   VAT / tax ID number (e.g. "SI78552478").
        partner_email:        Partner email address.
        partner_phone_number: Partner GSM/phone number.
        show_partner_discount: If True, include configured discount rules per product category.

    Returns:
        PartnerResult with count and list of matching partners,
        or PartnerError on failure.
    """
    require_permission("get_partner")
    return get_partner(
        partner_id=partner_id,
        partner_name=partner_name,
        partner_tax_number=partner_tax_number,
        partner_email=partner_email,
        partner_phone_number=partner_phone_number,
        show_partner_discount=show_partner_discount,
    )
