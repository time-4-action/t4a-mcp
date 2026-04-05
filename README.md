# T4A MCP Server + Knowledge Base

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes [MetaKocka ERP](https://www.metakocka.si/) operations and a company knowledge base as AI-callable tools. Secured by Auth0 JWT with role-based access control. Powers AI assistants (Claude, etc.) with live ERP data and indexed company documents.

---

## Architecture

```
AI Client (Claude/Next.js)
  └─► POST /api/chat
        ├─ Auth0 JWT obtained
        └─► MCP SSE connection  →  AuthMiddleware (JWT validation)
                                        └─► require_permission() (RBAC)
                                              ├─► MCP Tool  →  MetaKocka REST API
                                              │                 ChromaDB (product search)
                                              └─► company_knowledge  →  RAG pipeline
                                                                         ChromaDB + BM25 + Reranker
```

**Key components:**

| Component | Path | Description |
|---|---|---|
| FastAPI app | `src/server/app.py` | ASGI entry point, mounts MCP + auth middleware + knowledge routes |
| MCP tools | `src/server/tools/` | Tool implementations (products, docs, partners, knowledge, etc.) |
| Services | `src/server/services/` | MetaKocka API wrappers |
| Auth middleware | `src/server/auth.py` | Auth0 JWT validation (RS256, JWKS) |
| RBAC | `src/server/permissions.py` | Per-tool permission checks via `ContextVar` |
| Admin routes | `src/server/routes/admin.py` | Product reindex endpoint |
| Vector store | `src/vectorstore/` | ChromaDB + OpenAI embeddings for product search |
| Ingestion | `src/ingestion/` | Product and email data loading, cleaning, formatting |
| Knowledge pipeline | `app/pipeline/` | Parse → chunk → enrich → embed pipeline for company docs |
| Knowledge search | `app/search/` | BM25, hybrid RRF fusion, cross-encoder reranker |
| Knowledge routes | `app/routes/` | Admin API for uploading/indexing/managing knowledge sources |
| Config | `src/config.py`, `app/config.py` | Environment variable loading |

---

## Tools

All tools are exposed over MCP (SSE transport) at `/mcp`. Each tool requires a specific Auth0 permission — see [docs/tools_permissions.md](docs/tools_permissions.md) for the full matrix.

### Products

| Tool | Permission | Description |
|---|---|---|
| `identify_product` | `products:read` | Semantic vector search by name/description → returns SKU, EAN, similarity score |
| `get_product_price` | `products:read` | Price by SKU — default pricelist only; add `products:pricelists:read` to request any pricelist |
| `get_product_stock` | `warehouse:read` | Stock level for a single product in the configured warehouse |
| `get_product_url` | `products:read` | Webshop URL for a product SKU |
| `get_product_variants` | `products:read` | All published variants of a product (sizes, colours, etc.) |
| `get_product_pricelists` | `products:pricelists:read` | All pricelists for a product SKU |
| `list_pricelists` | `products:pricelists:read` | All available pricelists |

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

### Warehouse

| Tool | Permission | Description |
|---|---|---|
| `get_warehouse_list_tool` | `warehouse:read` | All configured warehouses (mark, name, address, type) |
| `get_warehouse_stock_tool` | `warehouse:read` | Bulk stock query — filter by warehouse, product code, or mk_id |

### Delivery

| Tool | Permission | Description |
|---|---|---|
| `get_delivery_service_pricelists_tool` | `delivery:pricelists:read` | All delivery service price lists with weight tiers and costs |

### Company Knowledge Base

| Tool | Permission | Description |
|---|---|---|
| `company_knowledge` | `knowledge:read` | Semantic search over indexed company documents (files, URLs, sitemaps) — hybrid dense + BM25 + reranking |

---

## Company Knowledge Base

The knowledge base ingests files, web pages, and sitemaps into a RAG pipeline and exposes them via the `company_knowledge` MCP tool.

### Indexing Pipeline

```
Source (file / URL / sitemap)
  └─► [1. Parse]          — unstructured (PDF/DOCX/XLSX), trafilatura (web)
  └─► [2. Chunk]          — parent (~800 tokens) + child (~200 tokens) splits
  └─► [3. Enrich]         — Claude Haiku prepends context to each child chunk
  └─► [4. Embed]          — OpenAI text-embedding-3-large (3072 dims)
  └─► [5a. ChromaDB]      — dense vectors (cosine similarity)
  └─► [5b. BM25 index]    — keyword index (rank_bm25, serialized to disk)
  └─► [MongoDB]           — source metadata, hashes, chunk IDs, parent chunk map
```

### Retrieval Pipeline

```
Query
  └─► Embed (text-embedding-3-large)
  └─► Dense search (ChromaDB, top-20)  ┐
  └─► BM25 keyword search (top-20)     ├─► RRF fusion → top-30
                                       ┘
  └─► Cross-encoder reranker (MiniLM, top-5)
  └─► Parent chunk expansion (fetch richer context from MongoDB)
  └─► Return passages + source attribution
```

### Admin API

All admin endpoints require `x-api-key` header (set `ADMIN_API_KEY` in `.env`).

| Endpoint | Description |
|---|---|
| `POST /admin/upload-file` | Upload PDF, DOCX, XLSX, TXT, CSV, HTML, MD |
| `POST /admin/add-url` | Index a single URL |
| `POST /admin/add-urls-bulk` | Index multiple URLs at once |
| `POST /admin/upload-sitemap` | Upload sitemap.xml → crawl and index all URLs |
| `POST /admin/reindex-company-data` | Re-crawl and re-index all sources (hash-based, skips unchanged) |
| `GET /admin/sources` | List all sources (filter by `type`, `status`; paginated) |
| `GET /admin/source/:id` | Source details |
| `DELETE /admin/source/:id` | Remove source + purge vectors |
| `POST /admin/source/:id/reindex` | Force reindex a single source |
| `GET /admin/stats` | Knowledge base overview (source counts, chunk counts) |
| `POST /admin/search-test` | Test the full retrieval pipeline with a query |

**Quick start — add your first sources:**
```bash
# Upload a PDF
curl -X POST https://<host>/admin/upload-file \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@handbook.pdf" -F "label=Company Handbook"

# Index a web page
curl -X POST https://<host>/admin/add-url \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-site.com/about", "label": "About page"}'

# Upload site sitemap
curl -X POST https://<host>/admin/upload-sitemap \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@sitemap.xml" -F "base_label=your-site.com"

# Test retrieval
curl -X POST https://<host>/admin/search-test \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "what services do you offer", "show_scores": true}'
```

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

### Auth0 Permissions Setup

Create the following permissions on your Auth0 API (Dashboard → **Applications → APIs → your API → Permissions tab**). The API identifier must match `AUTH0_MCP_AUDIENCE`.

| Permission | Description |
|---|---|
| `products:read` | Read product catalog — search products, view webshop URLs, variants, and pricing from the **default pricelist only** |
| `products:pricelists:read` | Access all pricelists — list available pricelists, view all pricelist prices for a product, and request pricing from any non-default pricelist via `get_product_price`. Requires `products:read` as a prerequisite. |
| `warehouse:read` | Read warehouse data — list warehouses and query stock levels across all or specific warehouses |
| `documents:read` | Read ERP documents — search and retrieve sales orders, invoices, purchase orders, warehouse documents, and their attachments |
| `partners:read` | Read partner/customer data — look up partners by name, email, tax number, phone, or internal ID |
| `delivery:pricelists:read` | Read delivery service pricing — view all delivery service price lists with weight tiers and costs |
| `knowledge:read` | Query the company knowledge base — semantic search over indexed company documents, files, and web pages |
| `admin:all` | Full administrative access — bypasses all per-tool permission checks; intended for service accounts and admins only |

### Roles

Create these roles in Auth0 (Dashboard → **User Management → Roles**) and attach the listed permissions to each role. Assign roles to users instead of individual permissions.

| Role | Scopes | Intended for |
|---|---|---|
| `product_viewer` | `products:read` | External tools or integrations that only need product search and default pricing |
| `sales` | `products:read`, `products:pricelists:read`, `partners:read`, `documents:read`, `delivery:pricelists:read` | Sales staff — full pricing visibility, partner lookup, order/invoice access |
| `warehouse` | `products:read`, `warehouse:read`, `documents:read` | Warehouse staff — stock levels, warehouse list, delivery notes and packing lists |
| `assistant` | all 7 scopes | General-purpose AI assistant that needs access to everything |
| `admin` | `admin:all` | Administrators and service-to-service integrations |

Add `knowledge:read` to any role whose users should be able to query the company knowledge base via the `company_knowledge` tool.

---

## Setup

### Prerequisites

- Python 3.11+
- OpenAI API key (embeddings)
- Anthropic API key (Claude Haiku for chunk enrichment)
- Auth0 tenant with an API configured (see [docs/auth_setup_guide.md](docs/auth_setup_guide.md))
- MetaKocka account with API access
- MongoDB instance (for knowledge source tracking)

### Local Development

```bash
# 1. Clone and create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies (torch CPU-only index as primary)
pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Start ChromaDB (required for both products and knowledge base)
docker run -d -p 8001:8000 \
  -v ./chroma_db:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e PERSIST_DIRECTORY=/chroma/chroma \
  chromadb/chroma:0.6.3

# 5. Run the server
uvicorn src.server.app:api --host 0.0.0.0 --port 8000 --reload
```

Server endpoints:
- `GET /` — service info
- `GET /health` — health check
- `/mcp` — MCP SSE endpoint (requires Auth0 JWT)
- `/admin/*` — knowledge base admin (requires `x-api-key`)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI key for `text-embedding-3-large` |
| `ANTHROPIC_API_KEY` | Yes | Anthropic key for Claude Haiku chunk enrichment |
| `AUTH0_DOMAIN` | Yes | Auth0 tenant domain, e.g. `dev-xxx.eu.auth0.com` |
| `AUTH0_MCP_AUDIENCE` | Yes | Auth0 API audience |
| `MK_SECRET_KEY` | Yes | MetaKocka API secret key |
| `MK_COMPANY_ID` | Yes | MetaKocka company ID |
| `MK_BASE_URL` | Yes | MetaKocka REST API base URL |
| `MK_WAREHOUSE_ID` | Yes | Default warehouse ID for stock queries |
| `PRODUCTS_API_URL` | Yes | Products export endpoint |
| `MONGO_URI` | Yes | MongoDB connection string (knowledge source tracking) |
| `MONGO_DB_NAME` | Yes | MongoDB database name (default: `t4a`) |
| `CHROMA_HOST` | Yes | ChromaDB service hostname (default: `chromadb`) |
| `CHROMA_PORT` | Yes | ChromaDB service port (default: `8000`) |
| `ADMIN_API_KEY` | Yes | `x-api-key` for all `/admin/*` endpoints |
| `API_KEY` | Optional | Static key for service-to-service MCP access (grants `admin:all`) |
| `GMAIL_EMAIL` | Optional | Gmail address for email ingestion |
| `GMAIL_APP_PASSWORD` | Optional | Gmail app password for IMAP |
| `ENRICH_MODEL` | Optional | Claude model for enrichment (default: `claude-haiku-4-5-20251001`) |
| `PARENT_CHUNK_SIZE` | Optional | Parent chunk size in chars (default: `800`) |
| `CHILD_CHUNK_SIZE` | Optional | Child chunk size in chars (default: `200`) |
| `TOP_K_RERANK` | Optional | Final results returned after reranking (default: `5`) |

---

## Docker

**Production (pull from Docker Hub):**
```bash
cp .env.example .env   # fill in values
docker compose up -d
```

**Build and push a new image locally:**
```bash
docker build -t etiamsi/t4a-mcp:latest .
docker push etiamsi/t4a-mcp:latest
```

**On the server — update to latest:**
```bash
docker compose pull && docker compose up -d
docker logs -f t4a-mcp
```

**Useful commands:**
```bash
docker compose logs -f t4a-mcp       # live app logs
docker compose logs -f t4a-chromadb  # ChromaDB logs
docker compose down                   # stop all
curl http://localhost:8000/health     # verify app
curl http://localhost:8001/api/v1/heartbeat  # verify ChromaDB
```

ChromaDB data is persisted via `./chroma_db` (mounted into both the app and ChromaDB containers). Products are re-indexed automatically on first start if the collection is empty (~2–5 min).

---

## Project Structure

```
.
├── README.md
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
│
├── src/                               # MCP server + ERP tools
│   ├── config.py                      # env var loading
│   ├── PROMPT.md                      # system prompt for AI client
│   ├── server/
│   │   ├── app.py                     # FastAPI + MCP app, auth middleware
│   │   ├── auth.py                    # Auth0 JWT validation
│   │   ├── permissions.py             # RBAC, ContextVar user storage
│   │   ├── routes/
│   │   │   └── admin.py               # Product reindex endpoint
│   │   ├── services/                  # MetaKocka API wrappers
│   │   └── tools/                     # MCP tool definitions
│   │       ├── company_knowledge.py   # Knowledge base MCP tool
│   │       ├── product_search.py
│   │       └── ...
│   ├── vectorstore/                   # Product search (ChromaDB)
│   │   ├── manager.py                 # init + auto-index on startup
│   │   ├── updater.py                 # incremental upsert
│   │   └── generator.py              # standalone generation script
│   └── ingestion/
│       └── sources/
│           ├── products/              # product ingestion pipeline
│           └── emails/                # email ingestion pipeline
│
├── app/                               # Company knowledge base
│   ├── config.py                      # Knowledge API settings
│   ├── auth.py                        # x-api-key dependency
│   ├── retrieval.py                   # Full retrieval chain
│   ├── db/
│   │   └── mongo.py                   # Motor async MongoDB client
│   ├── vector/
│   │   └── chroma.py                  # ChromaDB HTTP client helpers
│   ├── search/
│   │   ├── bm25.py                    # BM25 index (rank_bm25)
│   │   ├── hybrid.py                  # RRF fusion
│   │   └── reranker.py                # Cross-encoder (MiniLM)
│   ├── pipeline/
│   │   ├── parser.py                  # File + URL → text
│   │   ├── chunker.py                 # Parent-child splitting
│   │   ├── enricher.py                # Claude contextual enrichment
│   │   ├── embedder.py                # OpenAI embeddings
│   │   └── ingester.py                # Orchestration
│   └── routes/                        # Admin HTTP endpoints
│       ├── upload_file.py
│       ├── add_url.py
│       ├── add_urls_bulk.py
│       ├── upload_sitemap.py
│       ├── reindex.py
│       ├── sources.py
│       └── search_test.py
│
├── chroma_db/                         # ChromaDB persisted data (gitignored)
├── uploads/                           # Uploaded files (gitignored)
├── bm25_indexes/                      # BM25 index files (gitignored)
│
├── scripts/
│   └── generate_pdf.py
│
├── tests/
│
└── docs/
    ├── auth.md
    ├── auth_end_to_end.md
    ├── auth_setup_guide.md
    ├── docker.md
    ├── tools_reference.md
    ├── tools_permissions.md
    ├── roles.md
    └── features_roadmap.md
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

Available tools are automatically filtered to what the authenticated user's role permits. Grant `knowledge:read` to any role that should have access to the company knowledge base.

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
