# Deployment

This guide covers running the T4A MCP Server in production with Docker.

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env   # fill in values
docker compose up -d
```

This starts two services:
- **t4a-mcp** — the MCP server on port `8000`
- **t4a-chromadb** — ChromaDB on port `8001`

---

## Docker Hub Image

The production image is published to Docker Hub as `time4action/t4a-mcp:latest`.

### Build and Push Scripts

Every build is tagged with a timestamp (`YYYYMMDD-HHMMSS`). The `:latest` and `:dev` tags are only applied when explicitly requested via flags.

```bash
# Build with timestamp tag only
./scripts/build.sh

# Build and also tag as :dev (for testing)
./scripts/build.sh --dev

# Build and also tag as :latest (production release)
./scripts/build.sh --latest

# Both at once
./scripts/build.sh --latest --dev

# Push the timestamped image only
./scripts/push.sh

# Push timestamped + :latest
./scripts/push.sh --latest

# Push timestamped + :dev
./scripts/push.sh --dev

# Push all
./scripts/push.sh --latest --dev
```

Windows equivalents: `scripts\build.bat` and `scripts\push.bat` (same flags).

### Update a Running Server

```bash
docker compose pull && docker compose up -d
docker logs -f t4a-mcp
```

---

## Build Optimization

The Dockerfile uses a multi-stage build:

| Feature | Benefit |
|---|---|
| `python:3.11-slim` base | ~50 MB vs ~900 MB full image |
| Multi-stage build | Build deps excluded from final image |
| Layer caching | Requirements installed separately for fast rebuilds |
| `--no-cache-dir` | No pip cache in image |
| PyTorch CPU-only | Avoids pulling ~2 GB CUDA variant |

Expected final image size: **~300-400 MB**.

---

## Useful Commands

```bash
# Live logs
docker compose logs -f t4a-mcp
docker compose logs -f t4a-chromadb

# Stop all services
docker compose down

# Verify app health
curl http://localhost:8000/health

# Verify ChromaDB
curl http://localhost:8001/api/v1/heartbeat
```

---

## Data Persistence

ChromaDB data is persisted via `./chroma_db` (mounted into both the app and ChromaDB containers).

| Volume | Purpose |
|---|---|
| `./chroma_db` | ChromaDB vectors (products + knowledge) |
| `./uploads` | Uploaded knowledge base files |
| `./bm25_indexes` | Serialized BM25 keyword indexes |

Products are re-indexed automatically on first start if the collection is empty (~2-5 min).

---

## Health Checks

Both services have Docker health checks configured:

- **t4a-mcp:** `curl -f http://localhost:8000/health` (every 30s)
- **chromadb:** `curl -f http://localhost:8000/api/v1/heartbeat` (every 10s)

The app container waits for ChromaDB to be healthy before starting (`depends_on: condition: service_healthy`).

---

## Production Considerations

### Resource Limits

Add to `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### Security

- Secrets are passed via environment variables (not baked into the image)
- Health checks are enabled
- Runs with a minimal attack surface (`python:3.11-slim`)
- Logs are capped at 10 MB / 3 files per service

### Scaling

```bash
docker compose up -d --scale t4a-mcp=3
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Container won't start | `docker compose logs t4a-mcp` |
| ChromaDB not loading | Verify `chroma_db/` exists, check file permissions |
| Build is slow | Ensure BuildKit is enabled: `docker version \| grep BuildKit` |
| Image too large | Inspect layers: `docker history time4action/t4a-mcp:latest` |
