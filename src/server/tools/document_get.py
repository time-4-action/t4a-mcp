from src.server import mcp
from src.server.permissions import require_permission, with_permission_check
from src.server.services.document_get_service import get_document, DocumentResult, DocumentError


@mcp.tool()
@with_permission_check
def get_document_tool(
    doc_type: str,
    doc_id: str | None = None,
    doc_count_code: str | None = None,
    buyer_order: str | None = None,
    slim: bool = True,
    return_delivery_service_events: bool = False,
    return_delivery_stats: bool = False,
    return_document_info: bool = False,
    show_attachments: bool = False,
    show_tracking_url: bool = False,
) -> DocumentResult | DocumentError:
    """Fetch a single MetaKocka document by ID, count code, or buyer order reference.

    By default returns a slim summary (key fields only). Set slim=False to get the
    full raw document when you need all fields (e.g. for editing or deep inspection).

    Slim response includes: mk_id, count_code, doc_date, status_code, partner name,
    sum_all, sum_basic, currency_code, duo_payment, buyer_order, warehouse,
    doc_link_list, and product_list (code/name/amount/price/tax only).

    ALL supported doc_type values:
        Sales:
            "sales_order"                 — webshop/B2B orders (Prodajno naročilo)
            "sales_offer"                 — quotes/offers (Ponudba)
        Sales bills:
            "sales_bill_domestic"         — domestic invoices
            "sales_bill_foreign"          — foreign invoices
            "sales_bill_retail"           — retail invoices
            "sales_bill_prepaid"          — prepaid invoices
            "sales_bill_credit_note"      — credit notes
        Purchase:
            "purchase_order"              — purchase orders / naročilnica
            "purchase_bill_domestic"      — domestic purchase bills
            "purchase_bill_foreign"       — foreign purchase bills
            "purchase_bill_prepaid"       — prepaid purchase bills
            "purchase_bill_credit_note"   — purchase credit notes
        Warehouse docs:
            "warehouse_delivery_note"     — delivery notes (Nalog za odpremo)
            "warehouse_packing_list"      — packing lists (Dobavnica)
            "warehouse_receiving_note"    — receiving notes (Nalog za prejem)
            "warehouse_acceptance_note"   — acceptance notes (Prevzemnica)
            "warehouse_inventory"         — inventory snapshots
        Other:
            "transfer_order"              — inter-warehouse transfers
            "workorder"                   — work/production orders
            "complaint"                   — customer complaints

    Identification — provide exactly one:
        doc_id:         MetaKocka internal numeric ID (mk_id).
        doc_count_code: Human-readable document number (e.g. "PP-12345", "1-MK-500", "NR-001").
        buyer_order:    Buyer's own reference — sales_order only.

    Optional flags (use slim=False when requesting these, as they add extra fields):
        return_delivery_service_events: Carrier event history.
        return_delivery_stats:          Delivery timing stats.
        return_document_info:           Audit trail (who created/changed).
        show_attachments:               Attached file URLs.
        show_tracking_url:              Tracking URL in extra_column.

    Returns:
        DocumentResult with the document dict, or DocumentError on failure.
    """
    require_permission("get_document")

    extra: dict = {}
    if return_delivery_service_events:
        extra["return_delivery_service_events"] = "true"
    if return_delivery_stats:
        extra["return_delivery_stats"] = "true"
    if return_document_info:
        extra["return_document_info"] = "true"
    if show_attachments:
        extra["show_attachments"] = "true"
    if show_tracking_url:
        extra["show_tracking_url"] = "true"

    return get_document(
        doc_type=doc_type,
        doc_id=doc_id,
        doc_count_code=doc_count_code,
        buyer_order=buyer_order,
        extra_params=extra or None,
        slim=slim,
    )
