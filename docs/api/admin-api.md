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
