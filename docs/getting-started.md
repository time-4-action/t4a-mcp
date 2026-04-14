# Getting Started

This guide walks you through setting up the T4A MCP Server for local development.

---

## Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| Docker | 20+ | ChromaDB (required), optional for app |
| OpenAI API key | — | `text-embedding-3-large` embeddings |
| Anthropic API key | — | Claude Haiku chunk enrichment |
| Auth0 tenant | — | JWT authentication ([setup guide](auth/setup-guide.md)) |
| MetaKocka account | — | ERP API access |
| MongoDB instance | — | Knowledge source tracking |

---

## 1. Clone and Create a Virtual Environment

```bash
git clone <repo-url>
cd t4a-mcp

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

## 2. Install Dependencies

PyTorch CPU-only index is used as the primary source to avoid pulling the ~2 GB CUDA variant:

```bash
pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  -r requirements.txt
```

## 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual values. See [Environment Variables](environment-variables.md) for the full reference.

## 4. Start ChromaDB

ChromaDB is required by both the product vector search and the knowledge base:

```bash
docker run -d -p 8001:8000 \
  -v ./chroma_db:/chroma/chroma \
  -e IS_PERSISTENT=TRUE \
  -e PERSIST_DIRECTORY=/chroma/chroma \
  chromadb/chroma:0.6.3
```

## 5. Run the Server

```bash
uvicorn src.server.app:api --host 0.0.0.0 --port 8000 --reload
```

## 6. Verify

| Endpoint | URL | Description |
|---|---|---|
| Info | `GET /` | Service info |
| Health | `GET /health` | Health check |
| MCP | `/mcp` | MCP SSE endpoint (requires Auth0 JWT) |
| Admin | `/admin/*` | Knowledge base admin (requires `x-api-key`) |
| Admin UI | `/admin-ui` | Browser-based admin interface |

```bash
curl http://localhost:8000/health
```

---

## Connecting an AI Client

The MCP server uses **SSE transport**. To connect Claude or any MCP-compatible client:

```
Endpoint:   https://<your-host>/mcp
Transport:  SSE
Auth:       Authorization: Bearer <Auth0 JWT>
```

The client must obtain an Auth0 Access Token with `audience` set to `AUTH0_MCP_AUDIENCE`. See [Auth End-to-End](auth/end-to-end.md) for a complete Next.js + Claude implementation example.

Available tools are automatically filtered to what the authenticated user's role permits.

---

## Next Steps

- [Architecture](architecture.md) — understand the system design
- [MCP Tools Reference](api/tools-reference.md) — see all available tools
- [Deployment](deployment.md) — run in production with Docker
