# Architecture

The T4A MCP Server is a single FastAPI application that exposes two parallel subsystems: **MCP + ERP Tools** and a **Company Knowledge Base**. Both share ChromaDB for vector search and are secured by Auth0 JWT authentication.

---

## High-Level Data Flow

```
AI Client (Claude / Next.js / any MCP client)
  |
  +---> MCP SSE connection (/mcp)
          |
          +---> AuthMiddleware (JWT validation)
          |       |
          |       +---> require_permission() (RBAC)
          |               |
          |               +---> MCP Tool ---> MetaKocka REST API
          |               |                   ChromaDB (product search)
          |               |
          |               +---> company_knowledge ---> RAG Pipeline
          |                                            ChromaDB + BM25 + Reranker
          |
  +---> Admin API (/admin/*)
          |
          +---> x-api-key auth
                  |
                  +---> Upload / Index / Manage knowledge sources
```

---

## Component Map

| Component | Path | Description |
|---|---|---|
| **FastAPI app** | `src/server/app.py` | ASGI entry point, mounts MCP + auth middleware + admin routes |
| **MCP tools** | `src/server/tools/` | Tool implementations (products, docs, partners, knowledge, etc.) |
| **Services** | `src/server/services/` | Thin async wrappers around MetaKocka REST API calls |
| **Auth middleware** | `src/server/auth.py` | Auth0 JWT validation (RS256, JWKS, cached) |
| **RBAC** | `src/server/permissions.py` | Per-tool permission checks via `ContextVar` |
| **Product vector store** | `src/vectorstore/` | ChromaDB + OpenAI embeddings for semantic product search |
| **Ingestion** | `src/ingestion/` | Product and email data loading, cleaning, formatting |
| **Knowledge pipeline** | `app/pipeline/` | Parse -> chunk -> enrich -> embed pipeline for company docs |
| **Knowledge search** | `app/search/` | BM25, hybrid RRF fusion, cross-encoder reranker |
| **Knowledge routes** | `app/routes/` | Admin HTTP endpoints for knowledge management |
| **Config** | `src/config.py`, `app/config.py` | Environment variable loading |

---

## Subsystem 1: MCP + ERP Tools (`src/`)

The MCP server exposes MetaKocka ERP operations as AI-callable tools over SSE transport.

**Entry point:** `src/server/app.py` creates the FastAPI app, mounts the FastMCP SSE app at `/mcp`, registers all routers, and runs vectorstore init + reranker preload in the lifespan handler.

**Auth flow:**
1. `AuthMiddleware` (raw ASGI) intercepts all `/mcp` requests
2. Calls `src/server/auth.py:verify_token()` for Auth0 RS256 JWT validation
3. Stores the validated user in a `ContextVar` via `src/server/permissions.py:set_user()`

**RBAC:** Every tool calls `require_permission(tool_name)` at the top of its handler. The permission map lives in `src/server/permissions.py:TOOL_PERMISSIONS`. The `admin:all` scope bypasses all checks.

**Tools** are defined in `src/server/tools/` and decorated with `@mcp.tool()` (FastMCP). The `mcp` instance is created in `src/server/__init__.py`.

**Product vector search:** `src/vectorstore/manager.py` initializes on startup (synchronous ChromaDB HTTP client). Auto-indexes products if the collection is empty.

---

## Subsystem 2: Company Knowledge Base (`app/`)

A full RAG pipeline that ingests files, web pages, and sitemaps and exposes them via the `company_knowledge` MCP tool.

### Indexing Pipeline

```
Source (file / URL / sitemap)
  +---> [1. Parse]     -- unstructured (PDF/DOCX/XLSX), trafilatura (web)
  +---> [2. Chunk]     -- parent (~800 tokens) + child (~200 tokens) splits
  +---> [3. Enrich]    -- Claude Haiku prepends context to each child chunk
  +---> [4. Embed]     -- OpenAI text-embedding-3-large (3072 dims)
  +---> [5a. ChromaDB] -- dense vectors (cosine similarity)
  +---> [5b. BM25]     -- keyword index (rank_bm25, serialized to disk)
  +---> [MongoDB]      -- source metadata, hashes, chunk IDs, parent chunk map
```

### Retrieval Pipeline

```
Query
  +---> Embed (text-embedding-3-large)
  +---> Dense search (ChromaDB, top-20)  -+
  +---> BM25 keyword search (top-20)     -+--> RRF fusion -> top-30
  +---> Cross-encoder reranker (MiniLM, top-5)
  +---> Parent chunk expansion (from MongoDB)
  +---> Return passages + source attribution
```

For a deep-dive into every pipeline stage, see [Knowledge Base Internals](knowledge-base-internals.md).

---

## Project Structure

```
.
+-- README.md
+-- CLAUDE.md                              # Claude Code instructions
+-- Dockerfile
+-- docker-compose.yml
+-- nginx.conf
+-- requirements.txt
|
+-- src/                                   # MCP server + ERP tools
|   +-- config.py                          # env var loading
|   +-- PROMPT.md                          # system prompt for AI client
|   +-- server/
|   |   +-- app.py                         # FastAPI + MCP app, auth middleware
|   |   +-- auth.py                        # Auth0 JWT validation
|   |   +-- permissions.py                 # RBAC, ContextVar user storage
|   |   +-- routes/
|   |   |   +-- admin.py                   # Product reindex endpoint
|   |   +-- services/                      # MetaKocka API wrappers
|   |   +-- tools/                         # MCP tool definitions
|   |       +-- company_knowledge.py       # Knowledge base MCP tool
|   |       +-- product_search.py
|   |       +-- ...
|   +-- vectorstore/                       # Product search (ChromaDB)
|   |   +-- manager.py                     # init + auto-index on startup
|   |   +-- updater.py                     # incremental upsert
|   |   +-- generator.py                   # standalone generation script
|   +-- ingestion/
|       +-- sources/
|           +-- products/                  # product ingestion pipeline
|           +-- emails/                    # email ingestion pipeline
|
+-- app/                                   # Company knowledge base
|   +-- config.py                          # Knowledge API settings
|   +-- auth.py                            # x-api-key dependency
|   +-- retrieval.py                       # Full retrieval chain
|   +-- db/
|   |   +-- mongo.py                       # Motor async MongoDB client
|   +-- vector/
|   |   +-- chroma.py                      # ChromaDB HTTP client helpers
|   +-- search/
|   |   +-- bm25.py                        # BM25 index (rank_bm25)
|   |   +-- hybrid.py                      # RRF fusion
|   |   +-- reranker.py                    # Cross-encoder (MiniLM)
|   +-- pipeline/
|   |   +-- parser.py                      # File + URL -> text
|   |   +-- chunker.py                     # Parent-child splitting
|   |   +-- enricher.py                    # Claude contextual enrichment
|   |   +-- embedder.py                    # OpenAI embeddings
|   |   +-- ingester.py                    # Orchestration
|   +-- routes/                            # Admin HTTP endpoints
|       +-- upload_file.py
|       +-- add_url.py
|       +-- add_urls_bulk.py
|       +-- upload_sitemap.py
|       +-- reindex.py
|       +-- sources.py
|       +-- search_test.py
|
+-- docs/                                  # Documentation
+-- scripts/                               # Utility scripts
+-- chroma_db/                             # ChromaDB data (gitignored)
+-- uploads/                               # Uploaded files (gitignored)
+-- bm25_indexes/                          # BM25 indexes (gitignored)
```

---

## Cross-Cutting Concerns

- **ChromaDB** is shared by both subsystems (`products` and `company_knowledge` collections). `CHROMA_HOST`/`CHROMA_PORT` must point to the running ChromaDB service.
- **Auth0 JWT** secures all `/mcp` endpoints. Admin endpoints use a separate `x-api-key` header.
- **System prompt** (`src/PROMPT.md`) instructs the AI client on tool usage behavior.
