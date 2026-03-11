# MCP Server — Recommended Features

## Currently Implemented

| Tool | Description |
|------|-------------|
| `identify_product` | Search product vector store, return top N matches |
| `get_product_price` | Look up pricing by SKU (net, VAT, gross) |
| `get_product_stock` | Look up warehouse stock by SKU |
| `get_product_url` | Generate web URL for product search |
| `get_product_variants` | Get product variants and detailed descriptions |
| `get_warehouse_stock_tool` | Query raw stock levels across all warehouses |
| `get_warehouse_list_tool` | Fetch all configured warehouses |
| `get_partner_tool` | Search partners by ID, name, tax number, email, phone |
| `search_blacklist_partner_tool` | Check if a partner is blacklisted |
| `search_documents_tool` | Search documents by type with advanced filtering |
| `discover_document_filters` | Discover available query_advance filter types |
| `get_document_tool` | Fetch a single document by ID, count code, or buyer order ref |
| `get_document_url` | Generate direct MetaKocka UI link for a document |
| `search_tracking_code_tool` | Find sales order by tracking code or sticker barcode |
| `get_delivery_service_pricelists_tool` | Fetch all delivery service price lists |

---

## Recommended Features to Add

### High Priority — Core Business Operations

#### Document Creation & Management
- [ ] **Create Sales Order** (`documents_put_document_sales_order`) — place new orders programmatically
- [ ] **Create Sales Offer/Quote** (`documents_put_document_offer`) — quoting workflow
- [ ] **Create Purchase Order** (`documents_put_document_purchase_order`) — procurement automation
- [ ] **Create Transfer Order** (`documents_put_document_transfer_order`) — inter-warehouse transfers
- [ ] **Create Warehouse Document** (`documents_put_document_whdocs`) — warehouse operations
- [ ] **Update Sales Order** (`documents_update_document_sales_order`) — edit existing orders
- [ ] **Update Bill** (`documents_update_document_bill`) — edit issued bills
- [ ] **Delete Sales Order** (`documents_delete_document_sales_order`) — remove orders
- [ ] **Change Document Status** (`change_document_status`) — confirm, invoice, cancel documents

#### Partner Management
- [ ] **Add Partner** (`add_partner`) — create new customers/partners
- [ ] **Update Partner** (`update_partner`) — update partner details

---

### Medium Priority — Shipping & Payments

#### Shipping & Fulfillment
- [ ] **Mark Orders as Shipped** (`mark_orders_as_shipped`) — post-shipment workflow
- [ ] **Generate Shipping Sticker** (`generate_sticker`) — label generation for logistics

#### Payments & Transactions
- [ ] **Add Payment** (`add_payment`) — record payments against documents
- [ ] **Put Transaction** (`put_transaction`) — financial transaction recording

---

### Medium Priority — Product Management

- [ ] **Product List** (`product_list`) — paginated full product listing with stock/prices
- [ ] **Add Product** (`product_add`) — create new products
- [ ] **Update Product** (`product_update`) — update product data
- [ ] **Delete Product** (`product_delete`) — remove products
- [ ] **Add Partner Product Code** (`put_product_partner_code`) — customer-specific SKUs
- [ ] **Update Partner Product Code** (`update_product_partner_code`)
- [ ] **Delete Partner Product Code** (`delete_product_partner_code`)

---

### Lower Priority — Reporting & Accounting

- [ ] **Async Report Generation** (`report_async`) — business analytics reports
- [ ] **Accounting Export** (`accounting_export`) — financial data exports
- [ ] **Get Bank Statement** (`get_bank_statement`) — banking reconciliation
- [ ] **Get Bank Statement Status** (`get_bank_statement_status`)
- [ ] **Get Bank Compensation** (`get_bank_compensation`)
- [ ] **Send Bill to FURS** (`put_sales_bill_send_to_furs`) — tax authority submission (Slovenia)

---

### Lower Priority — Complaints & Returns

- [ ] **Create Complaint** (`create_complaint`) — log customer complaints/returns
- [ ] **Get Complaint** (`get_complaint`) — retrieve complaint details
- [ ] **Update Complaint** (`update_complaint`) — update complaint status

---

### Lower Priority — Advanced & Integrations

- [ ] **Warehouse Stock Sync** (`warehouse_stock_sync`) — sync stock across systems
- [ ] **Import Inventory** (`import_inventory`) — bulk inventory updates
- [ ] **Add File/Attachment** (`add_file`, `add_attachment`) — attach files to records
- [ ] **Order Change Warehouse** (`order_change_warehouse`) — reassign orders between warehouses
- [ ] **Order Forbidden Products** (`order_forbidden_products`) — manage product restrictions per order
- [ ] **Webhooks** (`webhooks`) — event-driven integrations
- [ ] **Add Webshop Terms of Use** (`add_webshop_terms_of_use`) — webshop payment terms
- [ ] **Send Message** (`send_message`) — internal messaging

---

## Suggested Implementation Order

1. **Change Document Status** — enables full order lifecycle automation
2. **Create Sales Order** — core transactional capability
3. **Add Payment** — completes the order-to-cash loop
4. **Mark Orders as Shipped** — logistics automation
5. **Add/Update Partner** — CRM capabilities
6. **Generate Shipping Sticker** — fulfillment workflow
7. **Create Purchase Order** — procurement automation
8. **Product CRUD** — product catalog management
