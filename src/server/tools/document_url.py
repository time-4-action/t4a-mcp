from pydantic import BaseModel, Field

from src.server import mcp
from src.server.permissions import require_permission, with_permission_check

_MK_BASE = "https://main.metakocka.si/index.jsp"

_FRAGMENT: dict[str, str] = {
    # Sales — internal keys
    "sales_order":               "prodaja_salesorder",
    "sales_offer":               "prodaja_ponudbe",
    "sales_bill_domestic":       "prodaja_racuni_domaci",
    "sales_bill_foreign":        "prodaja_racuni_tuji",
    "sales_bill_prepaid":        "prodaja_racuni_avansni",
    "sales_bill_credit_note":    "prodaja_racuni_dobropisi",
    # Purchase — internal keys
    "purchase_order":            "nabava_narocilnice",
    "purchase_bill_foreign":     "nabava_racuni_tuji",
    # FIXME: unknown fragments — need real MK URLs for these:
    # "sales_bill_retail":        "???",
    # "purchase_bill_domestic":   "???",
    # "purchase_bill_prepaid":    "???",
    # "purchase_bill_credit_note":"???",
    # "workorder":                "???",
    # "complaint":                "???",
    # Warehouse — internal keys
    "warehouse_receiving_note":  "skladisce_nalog_prevzem",
    "warehouse_acceptance_note": "skladisce_prevzemnica2",
    "warehouse_delivery_note":   "skladisce_nalog_odprema",
    "warehouse_packing_list":    "skladisce_dobavnica2",
    "warehouse_inventory":       "skladisce_inventure",
    "transfer_order":            "skladisce_medskladiscnice",
    # MetaKocka API native doc_type aliases (as returned in document responses)
    "racuni_racun":              "prodaja_racuni_tuji",
}


class DocumentUrl(BaseModel):
    url: str = Field(description="Direct MetaKocka UI link to the document.")


class DocumentUrlError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


@mcp.tool()
@with_permission_check
def get_document_url(doc_type: str, mk_id: str) -> DocumentUrl | DocumentUrlError:
    """Generate a direct MetaKocka UI link for a document.

    Supported doc_type values:
        Sales:
            "sales_order"              — webshop/B2B orders
            "sales_offer"              — quotes/offers
            "sales_bill_domestic"      — domestic invoices
            "sales_bill_foreign"       — foreign invoices
            "sales_bill_prepaid"       — prepaid invoices
            "sales_bill_credit_note"   — credit notes
        Purchase:
            "purchase_order"           — purchase orders
            "purchase_bill_foreign"    — foreign purchase bills
        Warehouse:
            "warehouse_receiving_note" — receiving notes
            "warehouse_acceptance_note"— acceptance notes
            "warehouse_delivery_note"  — delivery notes
            "warehouse_packing_list"   — packing lists
            "warehouse_inventory"      — inventory snapshots
            "transfer_order"           — inter-warehouse transfers

    Args:
        doc_type: Document type (see above).
        mk_id:    MetaKocka internal document ID (mk_id).

    Returns:
        DocumentUrl with the direct UI link, or DocumentUrlError if doc_type is unsupported.
    """
    require_permission("get_document")

    fragment = _FRAGMENT.get(doc_type)
    if not fragment:
        supported = ", ".join(sorted(_FRAGMENT))
        return DocumentUrlError(
            error=f"No UI link mapping for doc_type '{doc_type}'. Supported: {supported}"
        )

    return DocumentUrl(url=f"{_MK_BASE}#{fragment}?id={mk_id}")
