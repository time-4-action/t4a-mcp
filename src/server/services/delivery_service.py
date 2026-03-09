import requests
from pydantic import BaseModel, Field

from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL


class TrackingResult(BaseModel):
    mk_id: str = Field(description="MetaKocka document ID of the matched sales order.")
    count_code: str = Field(description="Human-readable order number (e.g. PP-123456).")
    buyer_order: str | None = Field(default=None, description="Buyer order reference.")
    tracking_code: str | None = Field(default=None, description="Primary tracking code.")
    return_tracking_code: str | None = Field(default=None, description="Return tracking code.")


class TrackingError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def search_tracking_code(
    tracking_code: str | None = None,
    sticker_code: str | None = None,
) -> TrackingResult | TrackingError:
    payload: dict = {"secret_key": MK_SECRET_KEY, "company_id": MK_COMPANY_ID}
    if tracking_code is not None:
        payload["tracking_code"] = tracking_code
    if sticker_code is not None:
        payload["sticker_code"] = sticker_code

    try:
        response = requests.post(f"{MK_BASE_URL}/search_tracking_code", json=payload)
        response.raise_for_status()
    except Exception as e:
        return TrackingError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return TrackingError(error=data.get("opr_desc") or data.get("opr_code_desc", "Unknown API error"))

    return TrackingResult(
        mk_id=data.get("mk_id", ""),
        count_code=data.get("count_code", ""),
        buyer_order=data.get("buyer_order"),
        tracking_code=data.get("tracking_code"),
        return_tracking_code=data.get("return_tracking_code"),
    )


class PricelistResult(BaseModel):
    count: int = Field(description="Number of price lists returned.")
    pricelists: list[dict] = Field(description="List of delivery service price lists.")


class PricelistError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def get_delivery_service_pricelists() -> PricelistResult | PricelistError:
    payload = {"secret_key": MK_SECRET_KEY, "company_id": MK_COMPANY_ID}

    try:
        response = requests.post(f"{MK_BASE_URL}/get_delivery_service_pricelist", json=payload)
        response.raise_for_status()
    except Exception as e:
        return PricelistError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return PricelistError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    pricelists = data.get("pricelist_list", [])
    return PricelistResult(count=int(data.get("pricelist_list_count", len(pricelists))), pricelists=pricelists)
