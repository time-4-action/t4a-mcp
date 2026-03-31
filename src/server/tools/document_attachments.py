from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.document_get_service import (
    get_invoice_attachments,
    InvoiceAttachmentsResult,
    InvoiceAttachmentsError,
)


@mcp.tool()
@with_permission_check
def get_invoice_attachments_tool(
    doc_type: str,
    doc_id: str | None = None,
    doc_count_code: str | None = None,
) -> InvoiceAttachmentsResult | InvoiceAttachmentsError:
    """Fetch all attachments (file URLs) for a specific MetaKocka invoice.

    Use this when the user asks to see, download, or list files/attachments
    attached to an invoice or bill.

    Supported doc_type values (bills only):
        "sales_bill_domestic"         — domestic sales invoices
        "sales_bill_foreign"          — foreign sales invoices
        "sales_bill_retail"           — retail sales invoices
        "sales_bill_prepaid"          — prepaid sales invoices
        "sales_bill_credit_note"      — sales credit notes
        "purchase_bill_domestic"      — domestic purchase bills
        "purchase_bill_foreign"       — foreign purchase bills
        "purchase_bill_prepaid"       — prepaid purchase bills
        "purchase_bill_credit_note"   — purchase credit notes
        "sales_order"                 — sales orders also support attachments

    Identification — provide exactly one:
        doc_id:         MetaKocka internal numeric ID (mk_id).
        doc_count_code: Human-readable document number (e.g. "PP-12345", "1-MK-500").

    Returns:
        InvoiceAttachmentsResult with a list of attachment URLs, or
        InvoiceAttachmentsError on failure.
    """
    require_permission("get_invoice_attachments")
    return get_invoice_attachments(
        doc_type=doc_type,
        doc_id=doc_id,
        doc_count_code=doc_count_code,
    )
