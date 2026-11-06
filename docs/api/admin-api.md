# Admin API Reference

All admin endpoints require the `x-api-key` header. Set `ADMIN_API_KEY` in `.env`.

The admin API manages the company knowledge base: uploading sources, indexing content, and testing retrieval.

---

## Endpoints

### Upload & Index

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/upload-file` | Upload PDF, DOCX, XLSX, TXT, CSV, HTML, or MD |
| `POST` | `/admin/add-url` | Index a single URL |
| `POST` | `/admin/add-urls-bulk` | Index multiple URLs at once |
| `POST` | `/admin/upload-sitemap` | Upload `sitemap.xml` and crawl + index all URLs |

### Reindexing

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/reindex-company-data` | Re-crawl and re-index all sources (hash-based, skips unchanged) |
| `POST` | `/admin/source/:id/reindex` | Force reindex a single source |

### Source Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/sources` | List all sources (filter by `type`, `status`; paginated) |
| `GET` | `/admin/source/:id` | Source details |
| `DELETE` | `/admin/source/:id` | Remove source and purge its vectors |

### Diagnostics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/stats` | Knowledge base overview (source counts, chunk counts) |
| `POST` | `/admin/search-test` | Test the full retrieval pipeline with a query |

---

## Examples

### Upload a PDF

```bash
curl -X POST https://<host>/admin/upload-file \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@handbook.pdf" \
  -F "label=Company Handbook"
```

### Index a Web Page

```bash
curl -X POST https://<host>/admin/add-url \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-site.com/about", "label": "About page"}'
```

### Index an Entire Sitemap

```bash
curl -X POST https://<host>/admin/upload-sitemap \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@sitemap.xml" \
  -F "base_label=your-site.com"
```

### Test Retrieval

```bash
curl -X POST https://<host>/admin/search-test \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "what services do you offer", "show_scores": true}'
```

### List All Sources

```bash
curl https://<host>/admin/sources \
  -H "x-api-key: YOUR_KEY"
```

### Delete a Source

```bash
curl -X DELETE https://<host>/admin/source/<source_id> \
  -H "x-api-key: YOUR_KEY"
```

---

## Browser UI

A browser-based admin interface is available at `/admin-ui` for managing sources without using `curl`.

---

## Agent API (read-only)

The T4A agent (t4a-agent) reads the knowledge base through two routes guarded by a separate key, `AGENT_READ_KEY` (`x-api-key` header). That key opens only these routes; `ADMIN_API_KEY` does not open them. If `AGENT_READ_KEY` is unset they answer `503`; a missing or wrong key gets `401`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/knowledge/search` | Same retrieval as the `company_knowledge` MCP tool (hybrid search, rerank, parent expansion), full text |
| `GET` | `/agent/knowledge/sources` | All indexed sources, newest first |

### Search

Body: `{"query": "...", "top_k": 5}` (`query` 1-500 chars, `top_k` 1-10, default 5).

```json
{
  "results": [
    {
      "source_id": "665f...",
      "source_title": "Warranty terms",
      "source_type": "file",
      "source_url": null,
      "text": "full parent chunk text (max 4000 chars)",
      "score": 7.31
    }
  ]
}
```

`source_url` is set for URL sources and `null` otherwise. `score` is the cross-encoder rerank score.

### Sources

```json
{
  "total": 1,
  "items": [
    {"source_id": "665f...", "title": "Warranty terms", "type": "file", "url": null, "chunks": 12, "created_at": "2026-10-01T09:00:00Z"}
  ]
}
```

```bash
curl -X POST https://mcp.time-4-action.com/agent/knowledge/search \
  -H "x-api-key: $AGENT_READ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "warranty period", "top_k": 5}'
```
