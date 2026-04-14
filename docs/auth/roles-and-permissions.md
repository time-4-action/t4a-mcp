# Auth0 Roles & Permissions

## viewer

Read-only access across core operations. For stakeholders, auditors, external observers.

- `documents:read`
- `sales_orders:read`
- `offers:read`
- `purchase_orders:read`
- `work_orders:read`
- `warehouse:read`
- `warehouse_docs:read`
- `transfer_orders:read`
- `products:read`
- `partners:read`
- `complaints:read`
- `delivery:tracking:read`
- `files:read`
- `bills:read`

---

## sales_rep

Day-to-day sales work — offers, orders, customers, delivery.

- `documents:read`
- `documents:create`
- `documents:update`
- `documents:status_change`
- `sales_orders:read`
- `sales_orders:create`
- `sales_orders:update`
- `offers:read`
- `offers:create`
- `offers:update`
- `products:read`
- `products:partner_codes:read`
- `products:source_stock:read`
- `partners:read`
- `partners:create`
- `partners:update`
- `partners:blacklist:read`
- `warehouse:read`
- `complaints:read`
- `complaints:create`
- `complaints:update`
- `delivery:pricelists:read`
- `delivery:tracking:read`
- `reports:read`
- `files:read`
- `files:upload`
- `attachments:write`
- `messages:send`
- `webshop:abandoned_carts:read`

---

## warehouse_op

Warehouse & fulfillment operations only.

- `documents:read`
- `documents:status_change`
- `sales_orders:read`
- `sales_orders:change_warehouse`
- `sales_orders:mark_shipped`
- `work_orders:read`
- `work_orders:create`
- `work_orders:update`
- `warehouse:read`
- `warehouse:stock_sync`
- `warehouse:import_inventory`
- `warehouse_docs:read`
- `warehouse_docs:create`
- `warehouse_docs:update`
- `transfer_orders:read`
- `transfer_orders:create`
- `transfer_orders:update`
- `purchase_orders:read`
- `products:read`
- `products:source_stock:read`
- `delivery:pricelists:read`
- `delivery:stickers:generate`
- `delivery:tracking:read`
- `files:read`
- `files:upload`
- `attachments:write`

---

## accountant

Finance, billing, payments, exports, FURS.

- `documents:read`
- `bills:read`
- `bills:create`
- `bills:update`
- `bills:send_to_furs`
- `bills:export_accounting`
- `sales_orders:read`
- `purchase_orders:read`
- `payments:read`
- `payments:create`
- `transactions:write`
- `bank_statements:read`
- `bank_statements:status`
- `bank_compensation:read`
- `cash_register:read`
- `reports:read`
- `reports:async`
- `files:read`
- `files:upload`
- `attachments:write`

---

## manager

Full operational access across all domains. No system/infrastructure tools.

- `documents:read`
- `documents:create`
- `documents:update`
- `documents:delete`
- `documents:status_change`
- `bills:read`
- `bills:create`
- `bills:update`
- `bills:send_to_furs`
- `bills:export_accounting`
- `sales_orders:read`
- `sales_orders:create`
- `sales_orders:update`
- `sales_orders:delete`
- `sales_orders:change_warehouse`
- `sales_orders:mark_shipped`
- `sales_orders:forbidden_products`
- `offers:read`
- `offers:create`
- `offers:update`
- `purchase_orders:read`
- `purchase_orders:create`
- `purchase_orders:update`
- `work_orders:read`
- `work_orders:create`
- `work_orders:update`
- `warehouse:read`
- `warehouse:stock_sync`
- `warehouse:import_inventory`
- `warehouse_docs:read`
- `warehouse_docs:create`
- `warehouse_docs:update`
- `transfer_orders:read`
- `transfer_orders:create`
- `transfer_orders:update`
- `products:read`
- `products:create`
- `products:update`
- `products:partner_codes:read`
- `products:partner_codes:write`
- `products:partner_codes:delete`
- `products:source_stock:read`
- `partners:read`
- `partners:create`
- `partners:update`
- `partners:blacklist:read`
- `partners:blacklist:write`
- `payments:read`
- `payments:create`
- `transactions:write`
- `bank_statements:read`
- `bank_statements:status`
- `bank_compensation:read`
- `cash_register:read`
- `reports:read`
- `reports:async`
- `complaints:read`
- `complaints:create`
- `complaints:update`
- `delivery:pricelists:read`
- `delivery:stickers:generate`
- `delivery:tracking:read`
- `files:read`
- `files:upload`
- `attachments:write`
- `messages:send`
- `webshop:terms_of_use:write`
- `webshop:abandoned_carts:read`
- `webshop:abandoned_carts:write`

---

## admin

Unrestricted. Bypasses all permission checks on the MCP server.

- `admin:all`
- *(all manager permissions implicitly included via bypass)*
- `products:delete`
- `webhooks:read`
- `webhooks:write`
- `webhooks:delete`
