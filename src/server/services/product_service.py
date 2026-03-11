from pydantic import BaseModel, Field

from src.vectorstore.manager import initialize_vectorstore
vectorstore = initialize_vectorstore()


class ProductPrice(BaseModel):
    """Successful price lookup result."""

    code: str = Field(description="Product SKU code.")
    name: str = Field(description="Product name.")
    pricelist_title: str = Field(description="Name of the matched pricelist (e.g. 'RRP 2026').")
    currency: str = Field(description="Three-letter currency code (e.g. 'EUR').")
    net_price: float = Field(description="Price excluding VAT.")
    vat_rate: float = Field(description="VAT percentage (e.g. 22.0 for 22%).")
    vat_amount: float = Field(description="Calculated VAT amount.")
    price_with_vat: float = Field(description="Final price including VAT.")


class ProductPriceError(BaseModel):
    """Returned when the price lookup fails."""

    code: str | None = Field(default=None, description="Product SKU code, if available.")
    name: str | None = Field(default=None, description="Product name, if available.")
    error: str = Field(description="Description of what went wrong.")


class ProductStock(BaseModel):
    """Successful stock lookup result."""

    title: str = Field(description="Product name/title.")
    amount: float = Field(description="Available stock quantity.")
    unit: str = Field(description="Unit of measurement (e.g. 'kos', 'kg').")


class ProductStockError(BaseModel):
    """Returned when the stock lookup fails."""

    code: str | None = Field(default=None, description="Product SKU code, if available.")
    error: str = Field(description="Description of what went wrong.")


class ProductVariant(BaseModel):
    """A single product variant."""

    code: str = Field(description="Product SKU code (e.g. 'P03200001092').")
    ean: str = Field(description="EAN barcode.")
    name: str = Field(description="Product variant name.")


class ProductVariants(BaseModel):
    """List of product variants with shared descriptions."""

    parent_code: str = Field(description="Parent product code.")
    parent_name: str = Field(description="Parent product name.")
    short_description: str = Field(description="Short description (same for all variants).")
    detailed_description: str = Field(description="Detailed description (same for all variants).")
    variants: list[ProductVariant] = Field(description="List of product variants.")


class ProductVariantsError(BaseModel):
    """Returned when variant lookup fails."""

    code: str = Field(description="SKU code that was searched.")
    error: str = Field(description="Description of what went wrong.")


def search_products(query: str, n: int = 5) -> list[dict]:
    """Return the top N products matching the query from the vector store."""
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=n)

    results = []
    for doc, score in docs_with_scores:
        results.append({
            "product_name": doc.metadata.get("product_name", ""),
            "code": doc.metadata.get("code", ""),
            "ean": doc.metadata.get("ean", ""),
            "score": round(float(score), 4),
            "content": doc.page_content,
        })
    return results


def _parse_price(value: str) -> float:
    """Parse a European-format price string (comma as decimal separator)."""
    return float(value.replace(",", "."))


def _resolve_price(pricelist: list[dict], preferred_titles: list[str]) -> dict | None:
    """Return the first pricelist entry whose title matches the priority list."""
    by_title = {entry["title"]: entry for entry in pricelist}
    for title in preferred_titles:
        if title in by_title:
            return by_title[title]
    return None


def get_price(count_code: str) -> ProductPrice | ProductPriceError:
    """Look up the pricelist for a product by count_code via MetaKocka API.

    Returns the best-matching price (based on PRICELISTS priority in config)
    with VAT calculated from tax_desc.
    """
    import requests
    from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL, PRICELISTS

    response = requests.post(
        f"{MK_BASE_URL}/json/product_list",
        json={
            "secret_key": MK_SECRET_KEY,
            "company_id": MK_COMPANY_ID,
            "code": count_code,
            "return_pricelist": "true",
        },
    )
    response.raise_for_status()
    data = response.json()

    if data.get("opr_code") != "0":
        return ProductPriceError(error=data.get("opr_code_desc", "Unknown API error"))

    product = data.get("product_list")
    if not product:
        return ProductPriceError(error=f"No product found for count_code '{count_code}'")

    # product_list can be a dict (single) or list
    if isinstance(product, list):
        product = product[0]

    pricelist = product.get("pricelist", [])
    entry = _resolve_price(pricelist, PRICELISTS)

    if not entry:
        return ProductPriceError(
            code=product.get("code"),
            name=product.get("name"),
            error="No matching pricelist found",
        )

    price_def = entry["price_def"]
    net_price = _parse_price(price_def["price"])
    vat_rate = float(price_def.get("tax_desc", "0"))
    vat_amount = round(net_price * vat_rate / 100, 2)
    price_with_vat = round(net_price + vat_amount, 2)

    return ProductPrice(
        code=product.get("code", ""),
        name=product.get("name", ""),
        pricelist_title=entry["title"],
        currency=entry.get("currency_code", "EUR"),
        net_price=net_price,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        price_with_vat=price_with_vat,
    )


def get_stock(sku: str, warehouse_id: str | None = None) -> ProductStock | ProductStockError:
    """Look up warehouse stock for a product by SKU via MetaKocka API.

    Returns stock information for the given warehouse (or the configured default)
    including amount, reservations (if enabled), and microlocation.
    """
    import requests
    from src.config import MK_SECRET_KEY, MK_COMPANY_ID, MK_BASE_URL, MK_WAREHOUSE_ID

    wh_id = warehouse_id if warehouse_id else MK_WAREHOUSE_ID

    response = requests.post(
        f"{MK_BASE_URL}/json/warehouse_stock",
        json={
            "secret_key": MK_SECRET_KEY,
            "company_id": MK_COMPANY_ID,
            "wh_id_list": wh_id,
            "product_code_list": sku,
        },
    )
    response.raise_for_status()
    data = response.json()

    if data.get("opr_code") != "0":
        return ProductStockError(code=sku, error=data.get("opr_code_desc", "Unknown API error"))

    stock_list = data.get("stock_list", [])

    # If no stock entries, need to get product name from product_list API
    if not stock_list:
        # Get product info to return proper title
        product_response = requests.post(
            f"{MK_BASE_URL}/json/product_list",
            json={
                "secret_key": MK_SECRET_KEY,
                "company_id": MK_COMPANY_ID,
                "code": sku,
            },
        )
        product_response.raise_for_status()
        product_data = product_response.json()

        if product_data.get("opr_code") != "0":
            return ProductStockError(code=sku, error="Product not found")

        product = product_data.get("product_list")
        if isinstance(product, list):
            product = product[0] if product else None

        if not product:
            return ProductStockError(code=sku, error="Product not found")

        return ProductStock(
            title=product.get("name", ""),
            amount=0.0,
            unit=product.get("unit", "pcs"),
        )

    # Sum up amounts across all entries (multiple rows per serial number)
    total_amount = sum(float(item.get("amount", 0)) for item in stock_list)

    # Use first entry for title and unit (same for all rows)
    first_stock = stock_list[0]

    return ProductStock(
        title=first_stock.get("title", ""),
        amount=total_amount,
        unit=first_stock.get("unit", "pcs"),
    )


def get_variants(sku: str) -> ProductVariants | ProductVariantsError:
    """Get all product variants for a given SKU from the products API.

    If SKU is found in child_products, return all children from that parent.
    If SKU is found as a parent code, return that parent's info.
    """
    import requests
    from src.config import PRODUCTS_API_URL

    try:
        response = requests.get(PRODUCTS_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return ProductVariantsError(code=sku, error=f"API request failed: {str(e)}")

    if not data.get("success"):
        return ProductVariantsError(code=sku, error="API returned unsuccessful response")

    products = data.get("data", [])

    # Search for SKU in child_products first
    for product in products:
        # Skip unpublished parent products entirely
        if not product.get("published", False):
            continue

        child_products = product.get("child_products", [])
        # Filter to only published child products
        published_children = [c for c in child_products if c.get("published", False)]

        for child in published_children:
            if child.get("code", "").upper() == sku.upper():
                # Found in child - return all published siblings
                variants = [
                    ProductVariant(
                        code=c.get("code", ""),
                        ean=c.get("ean_code", ""),
                        name=c.get("product_name", ""),
                    )
                    for c in published_children
                ]
                return ProductVariants(
                    parent_code=product.get("code", ""),
                    parent_name=product.get("product_name", ""),
                    short_description=product.get("short_description", ""),
                    detailed_description=product.get("detailed_description", ""),
                    variants=variants,
                )

    # Search for SKU as parent code
    for product in products:
        if product.get("code", "").upper() == sku.upper():
            # Skip unpublished parent products
            if not product.get("published", False):
                return ProductVariantsError(code=sku, error=f"Product '{sku}' is not published")

            # Found as parent - return parent info with published variants
            child_products = product.get("child_products", [])
            published_children = [c for c in child_products if c.get("published", False)]

            variants = [
                ProductVariant(
                    code=c.get("code", ""),
                    ean=c.get("ean_code", ""),
                    name=c.get("product_name", ""),
                )
                for c in published_children
            ]
            return ProductVariants(
                parent_code=product.get("code", ""),
                parent_name=product.get("product_name", ""),
                short_description=product.get("short_description", ""),
                detailed_description=product.get("detailed_description", ""),
                variants=variants,
            )

    return ProductVariantsError(code=sku, error=f"Product '{sku}' not found in products database")
