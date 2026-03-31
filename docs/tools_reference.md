# MCP Server — Functionality Reference

This server exposes MetaKocka ERP operations as MCP tools, secured by role-based permissions (Auth0 JWT).

---

## Product Tools

### `identify_product`
**Permission:** `products:read`

Semantic vector-search for a product by name, description, or partial match. Returns the top N matching products with SKU code, EAN, and similarity score. Use this when you have a product name or description and need the SKU.

### `get_product_price`
**Permission:** `products:read`

Fetches the price for a product by its SKU (`count_code`) from MetaKocka pricelists. Returns net price, VAT rate, VAT amount, and gross price. Uses the pricelist priority configured in `.env`.

### `get_product_stock`
**Permission:** `warehouse:read`

Returns stock levels for a single product by SKU in the configured warehouse. Returns quantity, unit, and (if reservations are enabled) reserved and free amounts. For bulk/multi-warehouse queries use `get_warehouse_stock_tool`.

### `get_product_url`
**Permission:** `products:read`

Returns the product page URL for a given SKU from the webshop product API.

### `get_product_variants`
**Permission:** `products:read`

Returns all published variants of a product (e.g. all sizes/colours of a parent product). Given any child SKU, finds the parent and returns all published siblings with their codes and EANs.

---

## Document Tools

### `search_documents_tool`
**Permission:** `documents:read`

Paginated search across MetaKocka documents. Always returns minimal `"ids"` results (mk_id, count_code). Use `get_document_tool` for details on specific records.

**Key doc_types:** `sales_order`, `sales_bill_domestic`, `sales_bill_foreign`, `sales_offer`, `purchase_order`, `warehouse_acceptance_note`, `warehouse_packing_list`, `transfer_order`, `workorder`

**`show_status_code=True`** — include `status_code` in each result without fetching full docs.

**Date filters** — values are auto-normalized (bare dates get `+02:00` appended):
- `doc_date_from` / `doc_date_to` — format `YYYY-MM-DD+02:00`
- `last_change_from` / `last_change_to` — format `YYYY-MM-DDThh:mm:ss+02:00`
- `status_change_from` / `status_change_to` + `status_change_list` — filter by status transition

**Status filtering:** Use `{"type": "status_list", "value": "draft,ready_to_ship"}` to filter directly. No post-processing needed.

### `discover_document_filters`
**Permission:** `documents:read`

Calls MetaKocka's filter discovery endpoint to list all valid `query_advance` filter types for a given `doc_type`. Call this before `search_documents_tool` if unsure which filters are available.

### `get_document_tool`
**Permission:** `documents:read`

Fetches a single document by `doc_id`, `doc_count_code`, or `buyer_order`.

By default returns a **slim summary** (key fields only): `mk_id`, `count_code`, `doc_date`, `status_code`, `partner` name, `sum_all`, `sum_basic`, `currency_code`, `duo_payment`, `buyer_order`, `warehouse`, `doc_link_list`, and a trimmed `product_list` (code/name/amount/price/tax). Set `slim=False` to get the full raw document.

**Supported doc_types:**

| doc_type | Description |
|---|---|
| `sales_order` | Webshop/B2B order |
| `sales_offer` | Quote/offer |
| `sales_bill_domestic` | Domestic sales invoice |
| `sales_bill_foreign` | Foreign sales invoice |
| `sales_bill_retail` | Retail invoice |
| `sales_bill_prepaid` | Prepaid invoice |
| `sales_bill_credit_note` | Credit note |
| `purchase_order` | Purchase order / naročilnica |
| `purchase_bill_domestic` | Domestic purchase bill |
| `purchase_bill_foreign` | Foreign purchase bill |
| `purchase_bill_prepaid` | Prepaid purchase bill |
| `purchase_bill_credit_note` | Purchase credit note |
| `warehouse_delivery_note` | Delivery note |
| `warehouse_packing_list` | Packing list / dobavnica |
| `warehouse_receiving_note` | Receiving note |
| `warehouse_acceptance_note` | Acceptance note / prevzemnica |
| `warehouse_inventory` | Inventory snapshot |
| `transfer_order` | Inter-warehouse transfer |
| `workorder` | Work/production order |
| `complaint` | Customer complaint |

**Optional flags** (use with `slim=False` for full data):
- `return_delivery_service_events` — carrier event history
- `return_delivery_stats` — delivery timing stats
- `return_document_info` — full audit trail
- `show_attachments` — attached file URLs
- `show_tracking_url` — tracking URL in `extra_column`

### `get_document_url`
**Permission:** `documents:read`

Generates a direct MetaKocka UI link for a document given its `doc_type` and `mk_id`. Returns a clickable URL of the form `https://main.metakocka.si/index.jsp#{fragment}?id={mk_id}`.

Supported doc_types: `sales_order`, `sales_offer`, `sales_bill_domestic`, `sales_bill_foreign`, `sales_bill_prepaid`, `sales_bill_credit_note`, `purchase_order`, `purchase_bill_foreign`, `warehouse_receiving_note`, `warehouse_acceptance_note`, `warehouse_delivery_note`, `warehouse_packing_list`, `warehouse_inventory`, `transfer_order`.

> **FIXME:** UI fragments unknown for `sales_bill_retail`, `purchase_bill_domestic`, `purchase_bill_prepaid`, `purchase_bill_credit_note`, `workorder`, `complaint`.

---

## Partner Tools

### `get_partner_tool`
**Permission:** `partners:read`

Searches MetaKocka partners (customers/suppliers) by name, email, tax number, phone, or internal ID. Returns contact details, delivery addresses, and optionally category discount rules.

### `search_blacklist_partner_tool`
**Permission:** `partners:blacklist:read`

Checks whether a partner is on the company blacklist by email, phone, or name. Use before accepting orders from unknown customers.

---

## Warehouse Tools

### `get_warehouse_list_tool`
**Permission:** `warehouse:read`

Returns all warehouses configured in MetaKocka with their mark (identifier used in orders/stock queries), name, address, type, and active status.

### `get_warehouse_stock_tool`
**Permission:** `warehouse:read`

Bulk stock query across warehouses. Filter by warehouse IDs, product codes, or product mk_ids. Returns per-warehouse, per-product stock entries including `amount`, `reserved_amount`, `free_amount`, and `microlocation`.

Use `get_warehouse_list_tool` to find warehouse IDs first.

---

## Delivery Tools

### `search_tracking_code_tool`
**Permission:** `delivery:tracking:read`

Finds a sales order by its delivery carrier tracking code or sticker barcode. Returns the order's `mk_id`, `count_code`, and associated tracking codes.

### `get_delivery_service_pricelists_tool`
**Permission:** `delivery:pricelists:read`

Returns all delivery service price lists configured in MetaKocka. Each entry includes the delivery type (e.g. "GLS Slovenija"), currency, and pricing tiers by package weight with transport cost, COD cost, and return cost.

---

## Roles & Permissions Summary

| Role | What they can do |
|---|---|
| `viewer` | Read-only: documents, products, partners, warehouse, complaints, bills, delivery tracking |
| `sales_rep` | viewer + create/update sales orders & offers, manage partners, file attachments, send messages |
| `warehouse_op` | Documents + mark shipped, change warehouse, sync stock, import inventory, create warehouse docs, generate stickers |
| `accountant` | Bills, payments, bank statements, transactions, cash register, accounting export, async reports |
| `manager` | Full operational access across all domains |
| `admin` | Unrestricted — bypasses all permission checks |

---

## Tool → Permission Mapping

| Tool | Required Permission |
|---|---|
| `identify_product` | `products:read` |
| `get_product_price` | `products:read` |
| `get_product_stock` | `warehouse:read` |
| `get_product_url` | `products:read` |
| `get_product_variants` | `products:read` |
| `search_documents_tool` | `documents:read` |
| `discover_document_filters` | `documents:read` |
| `get_document_tool` | `documents:read` |
| `get_document_url` | `documents:read` |
| `get_partner_tool` | `partners:read` |
| `search_blacklist_partner_tool` | `partners:blacklist:read` |
| `get_warehouse_list_tool` | `warehouse:read` |
| `get_warehouse_stock_tool` | `warehouse:read` |
| `search_tracking_code_tool` | `delivery:tracking:read` |
| `get_delivery_service_pricelists_tool` | `delivery:pricelists:read` |

---

## Not Yet Implemented (Planned)

### Write operations
- `change_document_status` — change order/document status
- `mark_orders_as_shipped` — bulk mark shipped
- `create_sales_order` / `update_sales_order`
- `create_sales_offer` / `update_sales_offer`
- `create_purchase_order` / `update_purchase_order`
- `create_warehouse_doc` / `update_warehouse_doc`
- `create_transfer_order` / `update_transfer_order`
- `create_workorder` / `update_workorder`
- `create_complaint` / `update_complaint`
- `add_partner` / `update_partner`
- `create_bill` / `update_bill` / `send_bill_to_furs`
- `add_payment`
- `add_attachment` / `add_file`
- `send_message`
- `generate_sticker`
- `sync_warehouse_stock` / `import_inventory`
- `order_change_warehouse`

### Read operations not yet implemented
- `get_bank_statement` / `get_bank_statement_status`
- `get_bank_compensation`
- `cash_register_journal`
- `get_source_stock` (external ERP stock)
- `get_order_forbidden_products`
- Reports (`report_concept`, `report_async`)
- `search_tracking_code` via abandoned carts
- Webhooks (admin only)
