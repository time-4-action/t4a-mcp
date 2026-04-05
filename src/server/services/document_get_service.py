import requests
from pydantic import BaseModel, Field

from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL

_session = requests.Session()
_MK_TIMEOUT = 15  # seconds


class DocumentResult(BaseModel):
    document: dict = Field(description="Document data returned by MetaKocka.")


class DocumentError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


_SLIM_TOP_FIELDS = frozenset({
    "mk_id", "doc_type", "count_code", "doc_date", "opr_code",
    "status_code", "status_desc", "currency_code",
    "sum_all", "sum_basic", "sum_discount", "sum_paid",
    "duo_payment", "buyer_order", "warehouse",
    "doc_link_list",
})

_SLIM_PRODUCT_FIELDS = frozenset({
    "mk_id", "code", "name", "amount", "price", "price_with_tax", "tax", "discount",
})


def _slim_document(doc: dict) -> dict:
    result = {k: v for k, v in doc.items() if k in _SLIM_TOP_FIELDS}
    if "partner" in doc and isinstance(doc["partner"], dict):
        result["partner"] = doc["partner"].get("customer") or doc["partner"].get("name")
    if "product_list" in doc and isinstance(doc["product_list"], list):
        result["product_list"] = [
            {k: v for k, v in p.items() if k in _SLIM_PRODUCT_FIELDS}
            for p in doc["product_list"]
        ]
        result["product_count"] = len(result["product_list"])
    return result


def get_document(
    doc_type: str,
    doc_id: str | None = None,
    doc_count_code: str | None = None,
    buyer_order: str | None = None,
    extra_params: dict | None = None,
    slim: bool = True,
) -> DocumentResult | DocumentError:
    """POST to MetaKocka /get_document and return the document."""
    payload: dict = {
        "secret_key": MK_SECRET_KEY,
        "company_id": MK_COMPANY_ID,
        "doc_type": doc_type,
    }
    if doc_id is not None:
        payload["doc_id"] = doc_id
    if doc_count_code is not None:
        payload["doc_count_code"] = doc_count_code
    if buyer_order is not None:
        payload["buyer_order"] = buyer_order
    if extra_params:
        payload.update(extra_params)

    try:
        response = _session.post(f"{MK_BASE_URL}/get_document", json=payload, timeout=_MK_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        return DocumentError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return DocumentError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    return DocumentResult(document=_slim_document(data) if slim else data)


class InvoiceAttachment(BaseModel):
    source_url: str = Field(description="Public URL to the attachment file.")
    file_name: str | None = Field(default=None, description="File name, if available.")


class InvoiceAttachmentsResult(BaseModel):
    doc_type: str = Field(description="Document type of the invoice.")
    doc_id: str | None = Field(default=None, description="MetaKocka internal document ID.")
    doc_count_code: str | None = Field(default=None, description="Human-readable document number.")
    attachments: list[InvoiceAttachment] = Field(description="List of attachments for the invoice.")


class InvoiceAttachmentsError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def get_invoice_attachments(
    doc_type: str,
    doc_id: str | None = None,
    doc_count_code: str | None = None,
) -> InvoiceAttachmentsResult | InvoiceAttachmentsError:
    """Fetch attachment list for a MetaKocka invoice."""
    payload: dict = {
        "secret_key": MK_SECRET_KEY,
        "company_id": MK_COMPANY_ID,
        "doc_type": doc_type,
        "show_attachments": "true",
    }
    if doc_id is not None:
        payload["doc_id"] = doc_id
    if doc_count_code is not None:
        payload["doc_count_code"] = doc_count_code

    try:
        response = _session.post(
            f"{MK_BASE_URL}/get_document",
            json=payload,
            timeout=_MK_TIMEOUT,
        )
        response.raise_for_status()
    except Exception as e:
        return InvoiceAttachmentsError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return InvoiceAttachmentsError(
            error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error")
        )

    raw_attachments = data.get("attachment_list") or []
    attachments = [
        InvoiceAttachment(
            source_url=a.get("source_url", ""),
            file_name=a.get("file_name"),
        )
        for a in raw_attachments
        if a.get("source_url")
    ]

    return InvoiceAttachmentsResult(
        doc_type=doc_type,
        doc_id=doc_id,
        doc_count_code=doc_count_code,
        attachments=attachments,
    )
