# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

T4A MCP Server — a [Model Context Protocol](https://modelcontextprotocol.io/) server exposing MetaKocka ERP operations and a company knowledge base as AI-callable tools. Secured with Auth0 JWT + role-based access control (RBAC). Uses SSE transport at `/mcp`.

## Development Commands

```bash
# Install dependencies (torch CPU-only index required)
pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  -r requirements.txt

# Start ChromaDB (required — used by both product search and knowledge base)
docker run -d -p 8001:8000 \
  -v ./chroma_db:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e PERSIST_DIRECTORY=/chroma/chroma \
  chromadb/chroma:0.6.3

# Run the server (development)
uvicorn src.server.app:api --host 0.0.0.0 --port 8000 --reload

# Docker (local)
docker compose up -d
```

Production deploys automatically: every push to `main` runs `.github/workflows/deploy.yml` (lint → build image to `ghcr.io/time-4-action/t4a-mcp:<sha>` → SSH deploy with health check and automatic rollback → public `/health` version check). Pull requests get the lint plus an image build and import smoke test. Details in `docs/deployment.md`.

Key endpoints: `/` (info), `/health`, `/mcp` (SSE, requires Auth0 JWT), `/admin/*` (requires `x-api-key`), `/admin-ui` (browser UI).

## Architecture

Two parallel subsystems share a single FastAPI app (`src/server/app.py:api`):

### 1. MCP + ERP Tools (`src/`)

- **Entry point**: `src/server/app.py` — FastAPI app that mounts the FastMCP SSE app at `/mcp`, registers all routers, and runs vectorstore init + reranker preload in the lifespan.
- **Auth flow**: `AuthMiddleware` (raw ASGI, in `app.py`) intercepts all `/mcp` requests, calls `src/server/auth.py:verify_token()` for Auth0 RS256 JWT validation, and stores the validated user in a `ContextVar` via `src/server/permissions.py:set_user()`.
- **RBAC**: Every tool calls `require_permission(tool_name)` at the top of its handler. The permission map lives in `src/server/permissions.py:TOOL_PERMISSIONS`. `admin:all` bypasses all checks. For mid-tool permission checks (e.g. restricting a parameter based on scope), use `has_permission(get_current_permissions(), [...])` — both helpers are in `permissions.py`.
- **Tools**: Defined in `src/server/tools/` and imported in `__init__.py`. Each tool is decorated with `@mcp.tool()` (FastMCP). The `mcp` instance is created in `src/server/__init__.py`.
- **Services**: `src/server/services/` — thin async wrappers around MetaKocka REST API calls.
- **Product vector search**: `src/vectorstore/manager.py` initializes on startup (synchronous ChromaDB HTTP client). Auto-indexes products if collection is empty.

### 2. Company Knowledge Base (`app/`)

- **Ingestion pipeline** (`app/pipeline/`): `parse_file`/`parse_url` → `build_parent_child_chunks` (parent ~800 tokens, child ~200 tokens) → Claude Haiku enrichment → OpenAI `text-embedding-3-large` → ChromaDB + BM25 index + MongoDB metadata.
- **Retrieval** (`app/retrieval.py:retrieve()`): embed query → hybrid search (dense ChromaDB + BM25, RRF fusion, top-30) → cross-encoder reranking (MiniLM, top-5) → parent chunk expansion from MongoDB.
- **Storage**: ChromaDB holds vectors for both products (`products` collection) and knowledge (`company_knowledge` collection). MongoDB tracks source metadata, content hashes, and the parent chunk map used for context expansion.
- **Admin routes** (`app/routes/`): file upload, URL indexing, sitemap crawl, reindex, source management — all protected by `x-api-key`.
- **MCP tool**: `src/server/tools/company_knowledge.py` calls `app/retrieval.py:retrieve()`.

### Key cross-cutting concerns

- `src/config.py` — loads ERP and auth env vars from `.env`
- `app/config.py` — loads knowledge base env vars (OpenAI key, Anthropic key, Mongo URI, chunk sizes, etc.)
- `CHROMA_HOST`/`CHROMA_PORT` — shared by both subsystems; must point to the running ChromaDB service
- `src/PROMPT.md` — system prompt for the AI client

## Adding a New Tool

1. Create `src/server/tools/<tool_name>.py`, decorate handler with `@mcp.tool()`, call `require_permission("<tool_name>")` as the first line.
2. Add the tool name and required permissions to `TOOL_PERMISSIONS` in `src/server/permissions.py`.
3. Import the tool in `src/server/tools/__init__.py`.
4. If it needs a MetaKocka API call, add a service in `src/server/services/`.

### Mid-tool permission checks (parameter-level scoping)

When a tool's behaviour depends on whether the user has an additional scope (e.g. restricting which pricelist they can request), check inside the handler after the main `require_permission` call:

```python
from src.server.permissions import require_permission, with_permission_check, has_permission, get_current_permissions

@mcp.tool()
@with_permission_check
def my_tool(param: str = DEFAULT) -> ...:
    require_permission("my_tool")          # gate on the base scope
    if param != DEFAULT and not has_permission(get_current_permissions(), ["extra:scope"]):
        raise PermissionError("Forbidden: 'extra:scope' required for non-default param")
    ...
```

`with_permission_check` catches the `PermissionError` and returns a structured error dict to the LLM.

### Auth0 scopes in use

| Scope | Grants |
|---|---|
| `products:read` | identify, price (default pricelist only), URL, variants |
| `products:pricelists:read` | list all pricelists, get all pricelists per product, request any pricelist in `get_product_price` |
| `warehouse:read` | stock per product, warehouse list, bulk stock |
| `documents:read` | search + get documents, invoice attachments |
| `partners:read` | partner lookup |
| `delivery:pricelists:read` | delivery service pricelists |
| `knowledge:read` | company knowledge base search |
| `admin:all` | bypasses all permission checks |

`DEFAULT_PRICELIST` is defined in `src/server/services/product_service.py` and must be imported by any tool that enforces the pricelist restriction.

### Auth0 roles

Assign these roles to users in Auth0 rather than individual scopes.

| Role | Scopes |
|---|---|
| `product_viewer` | `products:read` |
| `sales` | `products:read`, `products:pricelists:read`, `partners:read`, `documents:read`, `delivery:pricelists:read` |
| `warehouse` | `products:read`, `warehouse:read`, `documents:read` |
| `assistant` | all 7 scopes |
| `admin` | `admin:all` |

Add `knowledge:read` to any role that should access the `company_knowledge` tool.

## Environment Variables

Required: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AUTH0_DOMAIN`, `AUTH0_MCP_AUDIENCE`, `MK_SECRET_KEY`, `MK_COMPANY_ID`, `MK_BASE_URL`, `MK_WAREHOUSE_ID`, `PRODUCTS_API_URL`, `MONGO_URI`, `CHROMA_HOST`, `CHROMA_PORT`, `ADMIN_API_KEY`.

Optional: `API_KEY` (static key granting `admin:all` for service-to-service), `ENRICH_MODEL`, `PARENT_CHUNK_SIZE`, `CHILD_CHUNK_SIZE`, `TOP_K_RERANK`, `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`, `REINDEX_PRODUCTS_CRON`, `REINDEX_PRODUCTS_TZ`.

## Scheduled Product Reindex

Set `REINDEX_PRODUCTS_CRON` (standard 5-field crontab, e.g. `0 3 * * *`) to run the product reindex automatically in-process, with no dependency on an external trigger (n8n). `REINDEX_PRODUCTS_TZ` controls the timezone (default `UTC`). When `REINDEX_PRODUCTS_CRON` is unset/empty, the scheduler is not started and reindexing happens only on-demand via `POST /admin/reindex-products`. The scheduler (`src/server/scheduler.py`, APScheduler `AsyncIOScheduler`) is started/stopped in the app lifespan and runs `src/server/services/product_reindex.py:reindex_products` — the same logic the admin endpoint calls.
