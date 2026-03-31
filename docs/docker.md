# MCP Server Docker Deployment

Optimized Docker setup for fast builds and small image size.

## Quick Start

### 1. Setup Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual credentials
# Make sure to set OPENAI_API_KEY and other required variables
```

### 2. Build the Image

**Windows:**
```bash
build.bat
```

**Linux/Mac:**
```bash
chmod +x build.sh
./build.sh
```

**Or manually:**
```bash
docker build -t etiamsi/t4a-mcp:latest .
```

### 3. Run the Server

```bash
docker-compose up -d
```

### 4. Verify It's Running

```bash
# Check health
curl http://localhost:8000/health

# Check logs
docker-compose logs -f
```

## Build Optimization Features

### Fast Build Speed
- **Multi-stage build**: Separates build dependencies from runtime
- **Layer caching**: Requirements installed separately for fast rebuilds
- **BuildKit**: Modern build engine (enabled by default)
- **.dockerignore**: Excludes unnecessary files from build context

### Small Image Size
- **python:3.11-slim**: Minimal Python base (~50MB vs 900MB full image)
- **No cache**: `--no-cache-dir` during pip install
- **Single-stage runtime**: Only copies necessary artifacts
- **Cleanup**: Removes build dependencies after use

Expected final image size: **~300-400MB** (vs 1-2GB with full Python image)

## Deployment Commands

```bash
# Build
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f t4a-mcp

# Stop
docker-compose down

# Restart
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

## Server Endpoints

- **Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **MCP Endpoint**: http://localhost:8000/mcp

## Environment Variables

Required environment variables (set in `.env`):

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `MK_SECRET_KEY` | MK API secret key |
| `MK_COMPANY_ID` | MK company ID |
| `MK_BASE_URL` | MK API base URL |
| `MK_WAREHOUSE_ID` | MK warehouse ID |
| `PRODUCTS_API_URL` | Products API endpoint |

## ChromaDB Persistence

The ChromaDB vector store is included in the image by default.

**To update ChromaDB externally**, uncomment the volume mount in `docker-compose.yml`:

```yaml
volumes:
  - ./chroma_db:/app/chroma_db:ro
```

## Production Deployment

### Resource Limits

Adjust in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### Security

- Runs as non-root user (uid 1000)
- Secrets via environment variables (not baked in image)
- Health checks enabled
- Minimal attack surface

### Scaling

To run multiple instances:
```bash
docker-compose up -d --scale t4a-mcp=3
```

## Troubleshooting

### Build is slow
- Check if BuildKit is enabled: `docker version | grep BuildKit`
- Clear build cache: `docker builder prune`
- Check `.dockerignore` excludes large files

### Image is too large
- Check what's in the image: `docker image inspect etiamsi/t4a-mcp:latest`
- Look for large layers: `docker history etiamsi/t4a-mcp:latest`

### Container won't start
```bash
# Check logs
docker-compose logs t4a-mcp

# Check environment variables
docker-compose config

# Test health endpoint
curl http://localhost:8000/health
```

### ChromaDB not loading
- Verify `chroma_db/` directory exists and has data
- Check file permissions
- Check logs for initialization errors

## Development vs Production

**Development** (with live reload):
```bash
docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd)/mcp_server:/app/mcp_server \
  --env-file .env \
  etiamsi/t4a-mcp:latest \
  uvicorn mcp_server.server:api --host 0.0.0.0 --reload
```

**Production** (use docker-compose):
```bash
docker-compose up -d
```
