# Environment Variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env` to git.

---

## Required

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI key for `text-embedding-3-large` embeddings |
| `ANTHROPIC_API_KEY` | Anthropic key for Claude Haiku chunk enrichment |
| `AUTH0_DOMAIN` | Auth0 tenant domain, e.g. `dev-xxx.eu.auth0.com` |
| `AUTH0_MCP_AUDIENCE` | Auth0 API audience identifier |
| `MK_SECRET_KEY` | MetaKocka API secret key |
| `MK_COMPANY_ID` | MetaKocka company ID |
| `MK_BASE_URL` | MetaKocka REST API base URL |
| `MK_WAREHOUSE_ID` | Default warehouse ID for stock queries |
| `PRODUCTS_API_URL` | Products export endpoint |
| `MONGO_URI` | MongoDB connection string |
| `MONGO_DB_NAME` | MongoDB database name (default: `t4a`) |
| `CHROMA_HOST` | ChromaDB hostname (default: `chromadb`) |
| `CHROMA_PORT` | ChromaDB port (default: `8000`) |
| `ADMIN_API_KEY` | `x-api-key` for all `/admin/*` endpoints |

## Optional

| Variable | Description |
|---|---|
| `API_KEY` | Static key for service-to-service MCP access (grants `admin:all`) |
| `GMAIL_EMAIL` | Gmail address for email ingestion |
| `GMAIL_APP_PASSWORD` | Gmail app password for IMAP access |
| `ENRICH_MODEL` | Claude model for enrichment (default: `claude-haiku-4-5-20251001`) |
| `PARENT_CHUNK_SIZE` | Parent chunk size in chars (default: `800`) |
| `CHILD_CHUNK_SIZE` | Child chunk size in chars (default: `200`) |
| `TOP_K_RERANK` | Final results returned after reranking (default: `5`) |

## Configuration Files

| File | Purpose |
|---|---|
| `src/config.py` | Loads ERP and auth env vars |
| `app/config.py` | Loads knowledge base env vars (OpenAI, Anthropic, Mongo, chunk sizes, etc.) |
