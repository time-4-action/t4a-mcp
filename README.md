# T4A MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes [MetaKocka ERP](https://www.metakocka.si/) operations as AI-callable tools. Secured by Auth0 JWT with role-based access control. Powers AI assistants (Claude, etc.) with live ERP data: products, orders, partners, warehouse stock, and delivery.

---

## Architecture

```
AI Client (Claude/Next.js)
  └─► POST /api/chat
        ├─ Auth0 JWT obtained
        └─► MCP SSE connection  →  AuthMiddleware (JWT validation)
                                        └─► require_permission() (RBAC)
                                              └─► MCP Tool  →  MetaKocka REST API
                                                                ChromaDB (product search)
```

**Key components:**

| Component | Path | Description |
|---|---|---|
| FastAPI app | `src/server/app.py` | ASGI entry point, mounts MCP + auth middleware |
| MCP tools | `src/server/tools/` | Tool implementations (products, docs, partners, etc.) |
| Services | `src/server/services/` | MetaKocka API wrappers |
| Auth middleware | `src/server/auth.py` | Auth0 JWT validation (RS256, JWKS) |
| RBAC | `src/server/permissions.py` | Per-tool permission checks via `ContextVar` |
| Admin routes | `src/server/routes/admin.py` | Admin-only HTTP endpoints |
| Vector store | `src/vectorstore/` | ChromaDB + OpenAI embeddings for product search |
| Ingestion | `src/ingestion/` | Product and email data loading, cleaning, formatting |
| Config | `src/config.py` | Environment variable loading |

---

## Tools

All tools are exposed over MCP (SSE transport) at `/mcp`. Each tool requires a specific Auth0 permission — see [docs/tools_permissions.md](docs/tools_permissions.md) for the full matrix.

### Products

| Tool | Permission | Description |
|---|---|---|
| `identify_product` | `products:read` | Semantic vector search by name/description → returns SKU, EAN, similarity score |
| `get_product_price` | `products:read` | Price by SKU from MetaKocka pricelists (net, VAT, gross) |
| `get_product_stock` | `warehouse:read` | Stock level for a single product in the configured warehouse |
| `get_product_url` | `products:read` | Webshop URL for a product SKU |
| `get_product_variants` | `products:read` | All published variants of a product (sizes, colours, etc.) |
| `get_product_pricelists` | `products:read` | All pricelists for a product SKU |
| `list_pricelists` | `products:read` | All available pricelists |

### Documents

| Tool | Permission | Description |
|---|---|---|
| `search_documents_tool` | `documents:read` | Paginated search across all document types with advanced filters |
| `discover_document_filters` | — | Lists valid `query_advance` filter types for a given `doc_type` |
| `get_document_tool` | `documents:read` | Fetch a single document by ID, count code, or buyer order ref |
| `get_document_url` | — | Generates a direct MetaKocka UI link for a document |
| `get_invoice_attachments` | `documents:read` | Attachment URLs for an invoice |

Supported `doc_type` values: `sales_order`, `sales_offer`, `sales_bill_domestic`, `sales_bill_foreign`, `sales_bill_retail`, `sales_bill_prepaid`, `sales_bill_credit_note`, `purchase_order`, `purchase_bill_domestic`, `purchase_bill_foreign`, `warehouse_delivery_note`, `warehouse_packing_list`, `warehouse_acceptance_note`, `warehouse_inventory`, `transfer_order`, `workorder`, `complaint`.

### Partners

| Tool | Permission | Description |
|---|---|---|
| `get_partner_tool` | `partners:read` | Search partners by name, email, tax number, phone, or internal ID |
| `search_blacklist_partner_tool` | `partners:blacklist:read` | Check if a partner is on the company blacklist |

### Warehouse

| Tool | Permission | Description |
|---|---|---|
| `get_warehouse_list_tool` | `warehouse:read` | All configured warehouses (mark, name, address, type) |
| `get_warehouse_stock_tool` | `warehouse:read` | Bulk stock query — filter by warehouse, product code, or mk_id |

### Delivery

| Tool | Permission | Description |
|---|---|---|
| `search_tracking_code_tool` | `delivery:tracking:read` | Find a sales order by carrier tracking code or sticker barcode |
| `get_delivery_service_pricelists_tool` | `delivery:pricelists:read` | All delivery service price lists with weight tiers and costs |

---

## Authentication & Authorization

Every request to `/mcp/*` must carry a valid Auth0 JWT in the `Authorization: Bearer <token>` header.

**Validation steps (server-side):**
1. `AuthMiddleware` intercepts all `/mcp` requests before any handler runs
2. JWT header is parsed to extract `kid`; matching public key fetched from Auth0 JWKS (cached in-process)
3. `jose` library verifies: RS256 signature, `aud` == `AUTH0_MCP_AUDIENCE`, `iss` == Auth0 tenant, `exp` not expired
4. Validated user claims (`sub`, `email`, `permissions`) are stored in a `ContextVar` (per-request, async-safe)
5. Each tool calls `require_permission(tool_name)` before executing — raises `PermissionError` if the user lacks the required permission

`admin:all` permission bypasses all per-tool checks.

See [docs/auth.md](docs/auth.md) for the step-by-step flow and [docs/auth_end_to_end.md](docs/auth_end_to_end.md) for the full client+server walkthrough.

### Roles

| Role | Key Permissions |
|---|---|
| `viewer` | Read-only: documents, products, partners, warehouse, delivery tracking |
| `sales_rep` | viewer + create/update sales orders & offers, manage partners, send messages |
| `warehouse_op` | Documents + mark shipped, change warehouse, sync stock, generate stickers |
| `accountant` | Bills, payments, bank statements, transactions, cash register, accounting export |
| `manager` | Full operational access across all domains |
| `admin` | `admin:all` — bypasses all permission checks |

See [docs/roles.md](docs/roles.md) for the full permission list per role.

---

## Vector Store (Product Search)

Product identification (`identify_product`) uses ChromaDB with OpenAI `text-embedding-3-large` embeddings.

**Pipeline:**
```
MetaKocka Products API  →  loader  →  flattener  →  cleaner  →  formatter
                                                                     └─► ChromaDB (upsert)
```

- `src/ingestion/sources/products/loader.py` — fetches products from the API
- `src/ingestion/sources/products/flattener.py` — normalizes nested product data
- `src/ingestion/sources/products/cleaner.py` — strips noise, normalizes text
- `src/ingestion/sources/products/formatter.py` — creates embedding-optimized text
- `src/ingestion/sources/products/hasher.py` — content hashing for incremental updates
- `src/vectorstore/updater.py` — incremental upsert (only re-embeds changed products)
- `src/vectorstore/generator.py` — standalone generation script
- `src/vectorstore/manager.py` — initializes the store on server start; auto-indexes if empty

**Regenerate the vector store manually:**
```bash
python scripts/generate_vectorstore.py
```

**Pricelist priority** (configured in `src/config.py`):
```python
PRICELISTS = ["RRP 2026", "RRP 2025"]
```
`get_product_price` returns the price from the first pricelist that has an entry for the SKU.

---

## Setup

### Prerequisites

- Python 3.11+
- OpenAI API key (for embeddings)
- Auth0 tenant with an API configured (see [docs/auth_setup_guide.md](docs/auth_setup_guide.md))
- MetaKocka account with API access

### Local Development

```bash
# 1. Clone and create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Run the server
python -m src.server.app
# or
uvicorn src.server.app:api --host 0.0.0.0 --port 8000 --reload
```

Server endpoints:
- `GET /` — service info
- `GET /health` — health check + vectorstore status
- `/mcp` — MCP SSE endpoint (requires auth)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI key for `text-embedding-3-large` |
| `AUTH0_DOMAIN` | Yes | Auth0 tenant domain, e.g. `dev-xxx.eu.auth0.com` |
| `AUTH0_MCP_AUDIENCE` | Yes | Auth0 API audience, e.g. `https://api.your-company.com` |
| `MK_SECRET_KEY` | Yes | MetaKocka API secret key |
| `MK_COMPANY_ID` | Yes | MetaKocka company ID |
| `MK_BASE_URL` | Yes | MetaKocka REST API base URL |
| `MK_WAREHOUSE_ID` | Yes | Default warehouse ID for stock queries |
| `PRODUCTS_API_URL` | Yes | Products export endpoint |
| `API_KEY` | Optional | Static API key for service-to-service access (grants full access) |
| `GMAIL_EMAIL` | Optional | Gmail address for email ingestion |
| `GMAIL_APP_PASSWORD` | Optional | Gmail app password for IMAP |
| `GMAIL_IMAP_SERVER` | Optional | Defaults to `imap.gmail.com` |
| `GMAIL_IMAP_PORT` | Optional | Defaults to `993` |

---

## Docker

**Run from Docker Hub (production):**
```bash
cp .env.example .env   # fill in values
docker-compose up -d
```

**Build locally:**
```bash
# Windows
scripts\build.bat

# Linux/Mac
bash scripts/build.sh

# Manual
docker build -t etiamsi/t4a-mcp:latest .
```

**Useful commands:**
```bash
docker-compose logs -f t4a-mcp    # live logs
docker-compose up -d --build      # rebuild and restart
docker-compose down               # stop
curl http://localhost:8000/health  # verify
```

ChromaDB is persisted via a volume mount (`./chroma_db:/app/chroma_db`). The vector store is rebuilt automatically on first start if the collection is empty.

See [docs/docker.md](docs/docker.md) for full deployment details, resource limits, and troubleshooting.

---

## Project Structure

```
.
├── README.md
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
├── .env.example
│
├── src/
│   ├── config.py                          # env var loading
│   ├── PROMPT.md                          # system prompt for AI client
│   ├── server/
│   │   ├── app.py                         # FastAPI + MCP app, auth middleware
│   │   ├── auth.py                        # Auth0 JWT validation
│   │   ├── permissions.py                 # RBAC, ContextVar user storage
│   │   ├── routes/
│   │   │   └── admin.py                   # Admin HTTP endpoints
│   │   ├── services/                      # MetaKocka API wrappers
│   │   │   ├── delivery_service.py
│   │   │   ├── document_get_service.py
│   │   │   ├── document_service.py
│   │   │   ├── partner_service.py
│   │   │   ├── product_service.py
│   │   │   └── warehouse_service.py
│   │   └── tools/                         # MCP tool definitions
│   │       ├── delivery.py
│   │       ├── document_attachments.py
│   │       ├── document_get.py
│   │       ├── document_search.py
│   │       ├── document_url.py
│   │       ├── partner.py
│   │       ├── product_price.py
│   │       ├── product_pricelists.py
│   │       ├── product_search.py
│   │       ├── product_stock.py
│   │       ├── product_url.py
│   │       ├── product_variants.py
│   │       └── warehouse.py
│   ├── vectorstore/
│   │   ├── generator.py                   # standalone vectorstore generation
│   │   ├── manager.py                     # init + auto-index on startup
│   │   └── updater.py                     # incremental upsert
│   └── ingestion/
│       └── sources/
│           ├── products/                  # product ingestion pipeline
│           │   ├── cleaner.py
│           │   ├── flattener.py
│           │   ├── formatter.py
│           │   ├── hasher.py
│           │   └── loader.py
│           └── emails/                    # email ingestion pipeline
│               ├── cleaner.py
│               ├── formatter.py
│               └── loader.py
│
├── scripts/
│   ├── generate_vectorstore.py            # regenerate ChromaDB from scratch
│   ├── generate_pdf.py                    # utility script
│   ├── build.sh / build.bat               # Docker build scripts
│   └── push.sh / push.bat                 # Docker push scripts
│
├── chroma_db/                             # ChromaDB persisted data (gitignored)
│
├── tests/                                 # test suite
│
└── docs/
    ├── auth.md                            # Auth0 JWT flow (server side)
    ├── auth_end_to_end.md                 # Full client + server auth walkthrough
    ├── auth_setup_guide.md                # Auth0 dashboard setup guide
    ├── docker.md                          # Docker deployment guide
    ├── tools_reference.md                 # Full tool reference with all parameters
    ├── tools_permissions.md               # Tool → permission → role matrix
    ├── roles.md                           # Full permission list per role
    ├── features_roadmap.md                # Implemented features + planned work
    ├── metakocka_links.md                 # MetaKocka UI deep links reference
    └── metakocka/                         # MetaKocka API documentation
```

---

## Connecting an AI Client

The MCP server uses **SSE transport**. To connect Claude or any MCP-compatible client:

```
MCP endpoint: https://<your-host>/mcp
Transport:    SSE
Auth:         Authorization: Bearer <Auth0 JWT>
```

The client must obtain an Auth0 Access Token with `audience` set to `AUTH0_MCP_AUDIENCE`. See [docs/auth_end_to_end.md](docs/auth_end_to_end.md) for a complete Next.js + Claude implementation example.

Available tools are automatically filtered to what the authenticated user's role permits.

---

## Planned / Not Yet Implemented

See [docs/features_roadmap.md](docs/features_roadmap.md) for the full list. Highlights:

- Write operations: create/update sales orders, offers, purchase orders, warehouse docs, transfer orders
- Partner management: add/update partners
- Payments: add payment, put transaction
- Fulfillment: mark orders as shipped, generate stickers, change warehouse
- Product CRUD: add/update/delete products
- Finance: send bill to FURS, bank statements, accounting export
- Reports: async report generation
