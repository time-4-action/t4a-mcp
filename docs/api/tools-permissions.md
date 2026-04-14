# Tools & Permissions

Users with `admin:all` (role: `mk-admin`) bypass all permission checks.

## Products — `products:read`

Roles: `mk-viewer`, `mk-sales_rep`, `mk-warehouse_op`, `mk-manager`, `mk-admin`

| Tool | Description |
|------|-------------|
| `identify_product` | Search/identify a product |
| `get_product_price` | Get product price |
| `get_product_pricelists` | Get pricelists for a product |
| `list_pricelists` | List all available pricelists |
| `get_product_url` | Get product URL |
| `get_product_variants` | Get product variants |

## Warehouse — `warehouse:read`

Roles: `mk-viewer`, `mk-sales_rep`, `mk-warehouse_op`, `mk-manager`, `mk-admin`

| Tool | Description |
|------|-------------|
| `get_product_stock` | Get stock level for a product |
| `get_warehouse_list` | List all warehouses |
| `get_warehouse_stock` | Get stock levels per warehouse |

## Documents — `documents:read`

Roles: `mk-viewer`, `mk-sales_rep`, `mk-warehouse_op`, `mk-accountant`, `mk-manager`, `mk-admin`

| Tool | Description |
|------|-------------|
| `search_documents` | Search documents with filters |
| `get_document` | Get a single document by ID |
| `get_invoice_attachments` | Get attachments for an invoice |

## Partners — `partners:read`

Roles: `mk-viewer`, `mk-sales_rep`, `mk-manager`, `mk-admin`

| Tool | Description |
|------|-------------|
| `get_partner` | Get partner/customer info |

## Delivery — `delivery:pricelists:read`

Roles: `mk-sales_rep`, `mk-warehouse_op`, `mk-manager`, `mk-admin`

| Tool | Description |
|------|-------------|
| `get_delivery_service_pricelists` | Get delivery service pricelists |

## No permission required

All roles (including unauthenticated users with a valid token).

| Tool | Description |
|------|-------------|
| `discover_document_filters` | Discover available document filter options |
| `get_document_url` | Get a document URL |

---

## Role summary

| Role | products:read | warehouse:read | documents:read | partners:read | delivery:pricelists:read |
|------|:---:|:---:|:---:|:---:|:---:|
| `mk-viewer` | ✓ | ✓ | ✓ | ✓ | — |
| `mk-sales_rep` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `mk-warehouse_op` | ✓ | ✓ | ✓ | — | ✓ |
| `mk-accountant` | — | — | ✓ | — | — |
| `mk-manager` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `mk-admin` | ✓ | ✓ | ✓ | ✓ | ✓ |
