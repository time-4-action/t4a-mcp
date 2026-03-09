import requests
from pydantic import BaseModel, Field

from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL


class WarehouseListResult(BaseModel):
    count: int = Field(description="Number of warehouses returned.")
    warehouses: list[dict] = Field(description="List of warehouse records.")


class WarehouseStockResult(BaseModel):
    offset: int = Field(description="Pagination offset used.")
    limit: int = Field(description="Page size used.")
    stock_list: list[dict] = Field(description="Stock entries per product per warehouse.")


class WarehouseError(BaseModel):
    error: str = Field(description="Description of what went wrong.")


def get_warehouse_stock(
    wh_id_list: str | None = None,
    product_code_list: str | None = None,
    product_mk_id_list: str | None = None,
    eshop_sync: bool = False,
    offset: int = 0,
    limit: int = 100,
) -> WarehouseStockResult | WarehouseError:
    payload: dict = {
        "secret_key": MK_SECRET_KEY,
        "company_id": MK_COMPANY_ID,
        "offset": str(offset),
        "limit": str(limit),
    }
    if wh_id_list is not None:
        payload["wh_id_list"] = wh_id_list
    if product_code_list is not None:
        payload["product_code_list"] = product_code_list
    if product_mk_id_list is not None:
        payload["product_mk_id_list"] = product_mk_id_list
    if eshop_sync:
        payload["eshop_sync"] = "true"

    try:
        response = requests.post(f"{MK_BASE_URL}/json/warehouse_stock", json=payload)
        response.raise_for_status()
    except Exception as e:
        return WarehouseError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return WarehouseError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    return WarehouseStockResult(
        offset=int(data.get("offset", offset)),
        limit=int(data.get("limit", limit)),
        stock_list=data.get("stock_list", []),
    )


def get_warehouse_list() -> WarehouseListResult | WarehouseError:
    payload = {"secret_key": MK_SECRET_KEY, "company_id": MK_COMPANY_ID}

    try:
        response = requests.post(f"{MK_BASE_URL}/json/warehouse_list", json=payload)
        response.raise_for_status()
    except Exception as e:
        return WarehouseError(error=str(e))

    data = response.json()
    if data.get("opr_code") != "0":
        return WarehouseError(error=data.get("opr_code_desc") or data.get("opr_desc", "Unknown API error"))

    warehouses = data.get("warehouse_list", [])
    return WarehouseListResult(count=int(data.get("warehouse_list_count", len(warehouses))), warehouses=warehouses)
