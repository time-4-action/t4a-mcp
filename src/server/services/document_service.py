import re
import requests
from pydantic import BaseModel, Field

from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL


# Filters that need a full ISO datetime value (YYYY-MM-DDThh:mm:ss+HH:MM)
_DATETIME_FILTERS = frozenset({
    "last_change_from", "last_change_to",
    "tracking_last_event_date_from", "tracking_last_event_date_to",
    "status_change_from", "status_change_to",
})
# Filters that need a date-only value (YYYY-MM-DD+HH:MM)
_DATE_FILTERS = frozenset({
    "doc_date_from", "doc_date_to",
})

_TZ_SUFFIX = "+02:00"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_NO_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def _normalize_filter_value(filter_type: str, value: str) -> str:
    """Ensure date/datetime filter values include a timezone offset."""
    if filter_type in _DATE_FILTERS:
        # Expect YYYY-MM-DD+TZ — append +02:00 if bare date
        if _DATE_RE.match(value):
            return value + _TZ_SUFFIX
    elif filter_type in _DATETIME_FILTERS:
        # Expect YYYY-MM-DDThh:mm:ss+TZ — fill in time and TZ if needed
        if _DATE_RE.match(value):
            return value + "T00:00:00" + _TZ_SUFFIX
        if _DATETIME_NO_TZ_RE.match(value):
            return value + _TZ_SUFFIX
    return value


def _normalize_query_advance(filters: list[dict]) -> list[dict]:
    normalized = []
    for f in filters:
        if isinstance(f, dict) and "type" in f and "value" in f and isinstance(f["value"], str):
            normalized.append({"type": f["type"], "value": _normalize_filter_value(f["type"], f["value"])})
        else:
            normalized.append(f)
    return normalized


class FilterDiscovery(BaseModel):
    """Available query_advance filters per document type."""
    filters: dict[str, list[dict]] = Field(
        description="Mapping of doc_type to list of available filter objects, each with 'type', 'label', and 'value_desc'."
    )


class FilterDiscoveryError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def discover_filters(doc_type: str | None = None) -> FilterDiscovery | FilterDiscoveryError:
    """POST to MetaKocka /search_query_advance_discovery to list available query_advance filter types."""
    payload: dict = {"secret_key": MK_SECRET_KEY, "company_id": MK_COMPANY_ID}
    if doc_type:
        payload["doc_type"] = doc_type

    try:
        response = requests.post(f"{MK_BASE_URL}/search_query_advance_discovery", json=payload)
        response.raise_for_status()
    except Exception as e:
        return FilterDiscoveryError(error=str(e))

    data = response.json()
    if "opr_code" in data and data["opr_code"] != "0":
        return FilterDiscoveryError(error=data.get("opr_code_desc", "Unknown API error"))

    # Response is a dict of doc_type -> list of filter descriptors
    return FilterDiscovery(filters=data)


class SearchResult(BaseModel):
    """Successful document search result."""

    total_records: int = Field(description="Total number of matching records.")
    count: int = Field(description="Number of records returned in this page.")
    offset: int = Field(description="Pagination offset used.")
    limit: int = Field(description="Page size used.")
    results: list[dict] = Field(description="List of matching document records.")


class SearchError(BaseModel):
    """Returned when the document search fails."""

    error: str = Field(description="Description of what went wrong.")


def search_documents(
    doc_type: str,
    query: str | None = None,
    query_advance: list[dict] | None = None,
    result_type: str = "ids",
    limit: int = 20,
    offset: int = 0,
    order_direction: str | None = None,
    show_status_code: bool = False,
) -> SearchResult | SearchError:
    """POST to MetaKocka /search and return paginated document results."""
    payload: dict = {
        "secret_key": MK_SECRET_KEY,
        "company_id": MK_COMPANY_ID,
        "doc_type": doc_type,
        "result_type": result_type,
        "limit": limit,
        "offset": offset,
    }
    if query is not None:
        payload["query"] = query
    if query_advance is not None:
        payload["query_advance"] = _normalize_query_advance(query_advance)
    if order_direction is not None:
        payload["order_direction"] = order_direction
    if show_status_code:
        payload["show_status_code"] = "true"

    response = requests.post(f"{MK_BASE_URL}/search", json=payload)
    response.raise_for_status()
    data = response.json()

    if data.get("opr_code") != "0":
        return SearchError(error=data.get("opr_code_desc", "Unknown API error"))

    # result_type="doc" for purchase_product returns "result_product"; all others return "result"
    results = data.get("result") or data.get("result_product", [])
    if not isinstance(results, list):
        results = [results]

    return SearchResult(
        total_records=int(data.get("result_all_records", len(results))),
        count=int(data.get("result_count", len(results))),
        offset=int(data.get("offset", offset)),
        limit=int(data.get("limit", limit)),
        results=results,
    )
