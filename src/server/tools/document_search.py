from src.server import mcp
from src.server.permissions import require_permission
from src.server.services.document_service import (
    search_documents, SearchResult, SearchError,
    discover_filters, FilterDiscovery, FilterDiscoveryError,
)


@mcp.tool()
def discover_document_filters(doc_type: str | None = None) -> FilterDiscovery | FilterDiscoveryError:
    """Discover available query_advance filter types for MetaKocka document search.

    Call this BEFORE search_documents when you're unsure which filter types are
    valid for a given doc_type. Returns the exact filter 'type' strings, their
    labels, and expected value format.

    Args:
        doc_type: Limit results to one document type (e.g. "sales_order").
                  Omit to return filters for all document types.

    Returns:
        FilterDiscovery mapping doc_type to list of available filters,
        or FilterDiscoveryError on failure.
    """
    require_permission("search_documents")
    return discover_filters(doc_type=doc_type)


@mcp.tool()
def search_documents_tool(
    doc_type: str,
    query: str | None = None,
    query_advance: list[dict] | None = None,
    show_status_code: bool = False,
    limit: int = 20,
    offset: int = 0,
    order_direction: str | None = None,
) -> SearchResult | SearchError:
    """Search MetaKocka documents by type with optional filtering.

    Returns minimal results (mk_id, count_code). Use get_document_tool for details.
    Set show_status_code=True to also include status_code in each result (useful for
    filtering/displaying status without fetching full docs).

    IMPORTANT: Filter types (query_advance "type" values) are doc_type-specific.
    If unsure which filters are valid, call discover_document_filters first.

    Key doc_type values:
        - "sales_order"               — webshop/B2B orders
        - "sales_bill_domestic"       — domestic invoices
        - "sales_bill_foreign"        — foreign invoices
        - "purchase_bill_foreign"     — foreign purchase invoices
        - "warehouse_acceptance_note" — warehouse acceptance docs
        - "warehouse_packing_list"    — warehouse packing lists
        - "purchase_product"          — product catalog search

    DATE FORMAT — CRITICAL:
        doc_date_from / doc_date_to:
            Format: "YYYY-MM-DD+02:00"   e.g. "2024-01-15+02:00"
            Bare dates like "2024-01-15" are auto-normalized (TZ appended).

        last_change_from / last_change_to:
        status_change_from / status_change_to:
        tracking_last_event_date_from / tracking_last_event_date_to:
            Format: "YYYY-MM-DDThh:mm:ss+02:00"   e.g. "2024-01-15T00:00:00+02:00"
            Bare dates/datetimes without TZ are auto-normalized.

    Common query_advance filters:
        Date range:
            {"type": "doc_date_from",    "value": "2024-01-01+02:00"}
            {"type": "doc_date_to",      "value": "2024-12-31+02:00"}
            {"type": "last_change_from", "value": "2024-06-01T00:00:00+02:00"}
            {"type": "last_change_to",   "value": "2024-06-30T23:59:59+02:00"}
        Partner:
            {"type": "partner_recipient_name",  "value": "Acme d.o.o."}
            {"type": "partner_recipient_email", "value": "buyer@example.com"}
            {"type": "partner_tax_num",         "value": "SI12345678"}
        Status (use status_list to filter directly — no post-processing needed):
            {"type": "status_list",      "value": "draft,ready_to_ship"}
            {"type": "payment_status",   "value": "false"}  # bills only: "true"=paid
        Status change between dates (all three required together):
            {"type": "status_change_from", "value": "2024-01-01T00:00:00+02:00"}
            {"type": "status_change_to",   "value": "2024-12-31T23:59:59+02:00"}
            {"type": "status_change_list", "value": "canceled,lost,damaged"}
        Products:
            {"type": "product_code_list", "value": "SKU001,SKU002"}
            {"type": "product_id_list",   "value": "1600601820,1600601234"}
        Other:
            {"type": "customer_order",    "value": "PP-12345"}

    Args:
        doc_type: Document type to search (see above).
        query: Free-text search string across document fields.
        query_advance: List of {"type": ..., "value": ...} filter objects.
        show_status_code: Include status_code in each result (default False).
        limit: Page size (default 20, max 100).
        offset: Pagination offset (default 0).
        order_direction: "asc" or "desc".

    Returns:
        SearchResult with total_records, count, offset, limit, and results list,
        or SearchError if the API call fails.
    """
    require_permission("search_documents")
    return search_documents(
        doc_type=doc_type,
        query=query,
        query_advance=query_advance,
        result_type="ids",
        limit=limit,
        offset=offset,
        order_direction=order_direction,
        show_status_code=show_status_code,
    )
