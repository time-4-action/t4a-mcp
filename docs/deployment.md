# Deployment

This guide covers running the T4A MCP Server in production with Docker.

---

## Quick Start (local Docker Compose)

```bash
cp .env.example .env   # fill in values
docker compose up -d
```

This starts two services:
- **t4a-mcp** — the MCP server on port `8000`
- **t4a-chromadb** — ChromaDB on port `8001`

Production is deployed by CI on every push to `main`; see [CI/CD](#cicd).

---

## CI/CD

`.github/workflows/deploy.yml` (workflow `ci`) runs `check` → `deploy` → `verify`.

**check** runs on every pull request and every push to `main`: `ruff` for syntax
errors and undefined names (there is no test suite yet). On pull requests it also
builds the Docker image (not pushed) and imports the knowledge-base, auth and
scheduler modules inside it, so a broken `Dockerfile` or `requirements.txt` fails the pull
request rather than the deploy. A newer push to a pull request cancels its running
check; runs on `main` are queued, so pushes deploy strictly in order.

**deploy** runs only on `main` after a green check, one at a time. It builds the
image on GitHub Actions with the commit SHA baked in as `APP_VERSION`, pushes
`ghcr.io/time-4-action/t4a-mcp:<sha>` and `:latest` to GitHub Container Registry,
then SSHes to the VM as `deploy` and, in `/data/stack/apps/time-4-action/mcp`:

1. records the image the running `t4a-mcp` container uses;
2. logs in to `ghcr.io` with the job's own `GITHUB_TOKEN` (valid only while the job
   runs; logged out again on exit, so the VM stores no registry credential),
   `docker compose pull t4a-mcp` (three attempts) and `docker compose up -d t4a-mcp`
   with `APP_IMAGE` exported to the new SHA. ChromaDB is not restarted;
3. waits up to 3 minutes for `http://127.0.0.1:8000/health` to answer 200 (startup
   loads the reranker model before it listens);
4. checks the container reports `APP_VERSION` equal to the commit SHA.

If 3 or 4 fails it prints the logs, rolls back to the recorded image and fails the
run. **verify** then requests `/health` on the public URL
(`https://mcp.time-4-action.com`, override with the `PRODUCTION_URL` repository
variable) and requires its `version` field to equal the commit SHA.

`/health` answers 200 even when ChromaDB or MongoDB is `degraded`, so a database
outage never triggers a rollback.

The deploy only swaps images. `.env` and `docker-compose.yml` on the server are
edited by hand; the server copy of the compose file is `deploy/docker-compose.yml`
(the root one is for local use). To go back to an older release, re-run that
commit's workflow, or on the server:
`export APP_IMAGE=ghcr.io/time-4-action/t4a-mcp:<sha> && docker compose up -d t4a-mcp`
(a `docker login ghcr.io` first if the package is private).

### GitHub settings

Pushing and pulling the image use the workflow's `GITHUB_TOKEN` (`packages: write`
on the deploy job), so there is no registry secret. The
`org.opencontainers.image.source` label in the Dockerfile links the package to this
repository.

Organization secrets (shared with the other time-4-action repos on this VM),
available to the `production` environment:

| Secret | Value |
|---|---|
| `PROD_DEPLOY_HOST` | The VM's hostname or IP |
| `PROD_DEPLOY_SSH_KEY` | Private key whose public half is in `deploy`'s `authorized_keys` |
| `PROD_DEPLOY_FINGERPRINT` | `SHA256:…` from `ssh-keygen -lf /etc/ssh/ssh_host_ecdsa_key.pub` |

Optional repository variables: `PRODUCTION_URL`, `DEPLOY_USER` (default `deploy`),
`DEPLOY_DIR` (default `/data/stack/apps/time-4-action/mcp`). The SSH user must be in
the `docker` group, be able to write the server directory, and have `curl`.

### Server setup (once)

Replace the server's `docker-compose.yml` with `deploy/docker-compose.yml`. A copy
with a fixed `image:` tag (such as the old `etiamsi/t4a-mcp:latest`) ignores
`APP_IMAGE`, so every deploy would fail its `APP_VERSION` check and roll back. `.env`
sits beside it and holds the runtime secrets.

### Dependency updates

`.github/dependabot.yml` opens at most one grouped pull request per ecosystem a
month (pip minor + patch, the Docker base image's patch versions, GitHub Actions);
each goes through `check` like any other pull request.

### Manual build scripts

`scripts/build.sh` / `scripts/push.sh` (and the `.bat` versions) build and push
`time4action/t4a-mcp` to Docker Hub by hand. Production no longer uses them; deploy by
merging to `main`.

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
| Image too large | Inspect layers: `docker history ghcr.io/time-4-action/t4a-mcp:latest` |

## Production on t4a (since 2026-11-06)

Production moved from t2 to t4a (Hetzner, `77.42.42.60`; time-4-action/t4a-infra, `servers/t4a`), together with
the other apps on the shared `t4a` MongoDB database (t4a-partner-portal-api, t4a-admin, t4a-chat-ui, t4a-mcp).
Where this document says `/data/stack/apps/time-4-action/mcp` or nginx, that was t2.

- `/srv/mcp` (owned by `deploy`) holds `docker-compose.yml` (= `deploy/docker-compose.t4a.yml` in this repo: Traefik labels,
  loopback port 8000 for the deploy's health check) and `.env`, `chroma_db/`, `uploads/`, `bm25_indexes/` (copied at the cutover; ChromaDB has
  `company_knowledge` 2,184 and `products` 850 items). Traefik (`/srv/edge`) routes `mcp.time-4-action.com`
  here, behind Cloudflare.
- MongoDB is t4a's shared one (`/srv/mongo`): `MONGO_URI` is `mongodb://t4a-mcp:...@mongo:27017/t4a?authSource=t4a`
  (this app's own user, `readWrite` on `t4a`). The container joins the external `mongo` network.
- ChromaDB publishes no port any more; only `t4a-mcp` reaches it (`chromadb:8000`). The `mcp-cors` middleware
  answers browser preflight requests as nginx did.
- The `production` environment overrides the organization's deploy secrets: `PROD_DEPLOY_HOST` (`77.42.42.60`),
  `PROD_DEPLOY_SSH_KEY` (the key `github-actions@t4a-mcp-t4a`, public half in `/home/deploy/.ssh/authorized_keys`
  on t4a), `PROD_DEPLOY_FINGERPRINT` (t4a's **ECDSA** host key, `SHA256:2wkXWs0QETKFiXKXbxbJRASeNd9I6zigPKVQGBtwfTk`;
  the Ed25519 one fails with "host key fingerprint mismatch") and the variable `DEPLOY_DIR=/srv/mcp`.
- The move: the four apps stopped on t2 at 14:38 UTC, `mongodump` of `t4a` restored on t4a (all 34 collections'
  counts equal, 31,838 documents), the same images started on t4a, then the DNS records (proxied CNAMEs to
  `production.time-4-action.com`, overriding the `*` wildcard that still points at t2). About 4 minutes down.
  The t2 containers are stopped, not removed. To go back: delete the DNS record(s), the four settings above,
  copy the `t4a` database back, then `docker compose start` on t2 (for all four apps together).
