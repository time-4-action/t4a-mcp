#!/bin/bash
# Fast build script for MCP Server Docker image

set -e

echo "🐳 Building MCP Server Docker image..."
echo "=================================="

# Build with BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build \
  --progress=plain \
  -t etiamsi/t4a-mcp:latest \
  -t etiamsi/t4a-mcp:$(date +%Y%m%d-%H%M%S) \
  .

echo ""
echo "✅ Build complete!"
echo ""
echo "To run the server:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop:"
echo "  docker-compose down"
