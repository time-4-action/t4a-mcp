import requests
from pydantic import BaseModel, Field

from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL


class PartnerResult(BaseModel):
    count: int = Field(description="Number of partners returned.")
    partners: list[dict] = Field(description="List of partner records.")


class PartnerError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def get_partner(
    partner_id: str | None = None,
    partner_name: str | None = None,
    partner_tax_number: str | None = None,
    partner_email: str | None = None,
    partner_phone_number: str | None = None,
    show_partner_discount: bool = False,
) -> PartnerResult | PartnerError:
    payload: dict = {"secret_key": MK_SECRET_KEY, "company_id": MK_COMPANY_ID}
    if partner_id is not None:
        payload["partner_id"] = partner_id
    if partner_name is not None:
        payload["partner_name"] = partner_name
    if partner_tax_number is not None:
        payload["partner_tax_number"] = partner_tax_number
    if partner_email is not None:
        payload["partner_email"] = partner_email
    if partner_phone_number is not None:
        payload["partner_phone_number"] = partner_phone_number
    if show_partner_discount:
        payload["show_partner_discount"] = "true"

    try:
        response = requests.post(f"{MK_BASE_URL}/get_partner", json=payload)
        response.raise_for_status()
    except Exception as e:
        return PartnerError(error=str(e))

    data = response.json()
    if data.get("opr_code") not in (None, "0"):
        return PartnerError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    partners = data.get("partner_list", [])
    return PartnerResult(count=int(data.get("partner_list_count", len(partners))), partners=partners)


class BlacklistResult(BaseModel):
    count: int = Field(description="Number of blacklisted partners found.")
    partners: list[dict] = Field(description="List of blacklisted partner records.")


def search_blacklist_partner(
    api_user_email: str,
    partner_email: str | None = None,
    partner_phone_number: str | None = None,
    partner_name: str | None = None,
) -> BlacklistResult | PartnerError:
    payload: dict = {
        "secret_key": MK_SECRET_KEY,
        "company_id": MK_COMPANY_ID,
        "api_user_email": api_user_email,
    }
    if partner_email is not None:
        payload["partner_email"] = partner_email
    if partner_phone_number is not None:
        payload["partner_phone_number"] = partner_phone_number
    if partner_name is not None:
        payload["partner_name"] = partner_name

    try:
        response = requests.post(f"{MK_BASE_URL}/search_blacklist_partner", json=payload)
        response.raise_for_status()
    except Exception as e:
        return PartnerError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return PartnerError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    partners = data.get("partner_list", [])
    return BlacklistResult(count=int(data.get("partner_list_count", len(partners))), partners=partners)
