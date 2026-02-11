# Server Deployment Guide

## Prerequisites

Your server needs:
- Docker installed
- Docker Compose installed
- `.env` file with required variables

## Deployment Steps

### 1. Create a directory on your server

```bash
mkdir -p ~/t4a-mcp
cd ~/t4a-mcp
```

### 2. Create the .env file

```bash
nano .env
```

Paste this content (replace with your actual values):

```env
# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=sk-...

# MK API Configuration
MK_SECRET_KEY=your_secret_key
MK_COMPANY_ID=your_company_id
MK_BASE_URL=your_base_url
MK_WAREHOUSE_ID=your_warehouse_id

# Products API
PRODUCTS_API_URL=https://api.time-4-action.com/api/export/product
```

Save and exit (Ctrl+X, Y, Enter)

### 3. Create docker-compose.yml

```bash
nano docker-compose.yml
```

Paste this content:

```yaml
version: '3.8'

services:
  t4a-mcp:
    image: etiamsi/t4a-mcp:latest
    container_name: t4a-mcp
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Save and exit (Ctrl+X, Y, Enter)

### 4. Start the service

```bash
# Pull the latest image
docker-compose pull

# Start in background
docker-compose up -d

# Check if it's running
docker-compose ps
```

### 5. Verify it's working

```bash
# Check health endpoint
curl http://localhost:8000/health

# View logs
docker-compose logs -f
```

You should see: `{"status":"ok","vectorstore":"initialized"}`

## Common Commands

```bash
# View logs
docker-compose logs -f t4a-mcp

# Stop service
docker-compose down

# Restart service
docker-compose restart

# Update to latest version
docker-compose pull
docker-compose up -d

# Check resource usage
docker stats t4a-mcp
```

## Reverse Proxy Setup (Optional)

If you want to expose this to the internet with a domain name:

### Nginx

```nginx
server {
    listen 80;
    server_name mcp.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Caddy

```
mcp.yourdomain.com {
    reverse_proxy localhost:8000
}
```

## Firewall

If you want to access from outside the server:

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check if port is already in use
sudo lsof -i :8000
```

### Can't pull image

```bash
# Make sure you're logged in to Docker Hub
docker login

# Or if image is private, ask the owner to grant you access
```

### Check container health

```bash
# Manual health check
docker exec t4a-mcp curl -f http://localhost:8000/health

# View health status
docker inspect t4a-mcp | grep -A 10 Health
```

## Monitoring

### Basic monitoring with docker stats

```bash
# Real-time stats
docker stats t4a-mcp

# One-time stats
docker stats --no-stream t4a-mcp
```

### Log rotation

Logs are automatically rotated (max 10MB per file, 3 files kept).

To change this, edit docker-compose.yml:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"  # Change this
    max-file: "5"    # Change this
```

## Security Notes

- Never commit `.env` file to git
- Keep `.env` file permissions restricted: `chmod 600 .env`
- Use firewall to restrict access if needed
- Consider using Docker secrets for production

## Updating the Service

When a new version is released:

```bash
cd ~/t4a-mcp

# Pull latest image
docker-compose pull

# Restart with new image (zero-downtime)
docker-compose up -d

# Clean up old images
docker image prune -f
```
