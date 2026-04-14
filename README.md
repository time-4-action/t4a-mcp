<p align="center">
  <h1 align="center">T4A MCP Server</h1>
  <p align="center">
    AI-callable ERP tools and company knowledge base over the Model Context Protocol
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/MCP-SSE_transport-8B5CF6?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTUtMTAtNXoiLz48cGF0aCBkPSJNMiAxN2wxMCA1IDEwLTUiLz48cGF0aCBkPSJNMiAxMmwxMCA1IDEwLTUiLz48L3N2Zz4=" alt="MCP SSE">
  <img src="https://img.shields.io/badge/Auth0-JWT_RBAC-EB5424?logo=auth0&logoColor=white" alt="Auth0">
  <img src="https://img.shields.io/badge/ChromaDB-vector_search-FF6F00" alt="ChromaDB">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

---

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes [MetaKocka ERP](https://www.metakocka.si/) operations and a company knowledge base as AI-callable tools. Secured by **Auth0 JWT** with **role-based access control**. Powers AI assistants (Claude, etc.) with live ERP data and indexed company documents.

## Architecture

```
AI Client (Claude / Next.js / any MCP client)
  |
  +---> MCP SSE (/mcp)  --->  Auth0 JWT Validation  --->  RBAC
  |                              |
  |                              +---> ERP Tools ---------> MetaKocka REST API
  |                              |                          ChromaDB (product search)
  |                              |
  |                              +---> Knowledge Tool ----> RAG Pipeline
  |                                                         ChromaDB + BM25 + Reranker
  |
  +---> Admin API (/admin/*) ---> x-api-key auth
                                    |
                                    +---> Upload / Index / Search knowledge sources
```

**Two subsystems, one server:**

| Subsystem | Path | What it does |
|---|---|---|
| MCP + ERP Tools | `src/` | Exposes MetaKocka operations as AI-callable tools over SSE |
| Knowledge Base | `app/` | RAG pipeline: ingest documents, embed, hybrid search, rerank |

## MCP Tools

All tools are exposed at `/mcp` via SSE transport. Each requires a specific Auth0 permission.

### Products

| Tool | Permission | Description |
|---|---|---|
| `identify_product` | `products:read` | Semantic vector search by name/description |
| `get_product_price` | `products:read` | Price by SKU (default pricelist, or any with `products:pricelists:read`) |
| `get_product_stock` | `warehouse:read` | Stock level for a single product |
| `get_product_url` | `products:read` | Webshop URL for a product |
| `get_product_variants` | `products:read` | All published variants (sizes, colours, etc.) |
| `get_product_pricelists` | `products:pricelists:read` | All pricelists for a product |
| `list_pricelists` | `products:pricelists:read` | All available pricelists |

### Documents

| Tool | Permission | Description |
|---|---|---|
| `search_documents_tool` | `documents:read` | Paginated search with advanced filters |
| `get_document_tool` | `documents:read` | Fetch document by ID, count code, or buyer order ref |
| `discover_document_filters` | -- | List valid filter types for a doc_type |
| `get_document_url` | -- | Direct MetaKocka UI link |
| `get_invoice_attachments` | `documents:read` | Attachment URLs for an invoice |

### Partners, Warehouse & Delivery

| Tool | Permission | Description |
|---|---|---|
| `get_partner_tool` | `partners:read` | Search by name, email, tax number, phone, or ID |
| `get_warehouse_list_tool` | `warehouse:read` | All configured warehouses |
| `get_warehouse_stock_tool` | `warehouse:read` | Bulk stock query with filters |
| `get_delivery_service_pricelists_tool` | `delivery:pricelists:read` | Delivery price lists with weight tiers |

### Knowledge Base

| Tool | Permission | Description |
|---|---|---|
| `company_knowledge` | `knowledge:read` | Semantic search over indexed company documents |

> See [docs/api/tools-reference.md](docs/api/tools-reference.md) for full parameter details and [docs/api/tools-permissions.md](docs/api/tools-permissions.md) for the complete permission matrix.

## Knowledge Base Pipeline

The knowledge base ingests files, web pages, and sitemaps into a state-of-the-art RAG pipeline.

**Indexing:** Source --> Parse --> Parent-Child Chunk --> Claude Haiku Enrichment --> OpenAI Embed --> ChromaDB + BM25

**Retrieval:** Query --> Embed --> Dense + BM25 (RRF fusion, top-30) --> Cross-encoder rerank (top-5) --> Parent expansion

Manage sources via the [Admin API](docs/api/admin-api.md) or the browser UI at `/admin-ui`.

## Roles

| Role | Access |
|---|---|
| `product_viewer` | Product search + default pricing |
| `sales` | Products, pricelists, partners, documents, delivery pricing |
| `warehouse` | Products, stock levels, warehouse list, documents |
| `assistant` | All 7 scopes |
| `admin` | Bypasses all permission checks |

> Add `knowledge:read` to any role that should query the knowledge base.

## Quick Start

```bash
# 1. Install dependencies (torch CPU-only)
pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  -r requirements.txt

# 2. Configure
cp .env.example .env   # edit with your values

# 3. Start ChromaDB
docker run -d -p 8001:8000 \
  -v ./chroma_db:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e PERSIST_DIRECTORY=/chroma/chroma \
  chromadb/chroma:0.6.3

# 4. Run
uvicorn src.server.app:api --host 0.0.0.0 --port 8000 --reload
```

**Production (Docker Compose):**

```bash
docker compose up -d
```

> See [docs/getting-started.md](docs/getting-started.md) for the full setup walkthrough and [docs/deployment.md](docs/deployment.md) for production deployment.

## Connect an AI Client

```
Endpoint:   https://<your-host>/mcp
Transport:  SSE
Auth:       Authorization: Bearer <Auth0 JWT>
```

The client must obtain an Auth0 Access Token with `audience` set to `AUTH0_MCP_AUDIENCE`. See [docs/auth/end-to-end.md](docs/auth/end-to-end.md) for a complete Next.js + Claude integration walkthrough.

## Documentation

| Guide | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Prerequisites, local setup, first run |
| [Architecture](docs/architecture.md) | System design, data flow, component map |
| [Environment Variables](docs/environment-variables.md) | All configuration options |
| [Deployment](docs/deployment.md) | Docker, production, update workflow |
| [Auth Overview](docs/auth/overview.md) | JWT validation and RBAC internals |
| [Auth End-to-End](docs/auth/end-to-end.md) | Full client + server walkthrough |
| [Auth0 Setup](docs/auth/setup-guide.md) | Configuring Auth0 API and roles |
| [Roles & Permissions](docs/auth/roles-and-permissions.md) | Role definitions and scope assignments |
| [Tools Reference](docs/api/tools-reference.md) | Every tool: parameters, permissions, behavior |
| [Permissions Matrix](docs/api/tools-permissions.md) | Tool-to-scope and role-to-scope matrices |
| [Admin API](docs/api/admin-api.md) | Knowledge base admin endpoints |
| [Knowledge Base Internals](docs/knowledge-base-internals.md) | RAG pipeline deep-dive |
| [Roadmap](docs/api/roadmap.md) | Planned features and priority |
| [MetaKocka API Reference](docs/metakocka/) | Full MetaKocka REST API docs |

## License

Private repository. All rights reserved.
