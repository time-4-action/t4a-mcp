#!/bin/bash
# Fast build script for MCP Server Docker image
# Usage: ./build.sh [--latest] [--dev]

set -e

IMAGE="time4action/t4a-mcp"
TAG=$(date +%Y%m%d-%H%M%S)

TAGS="-t $IMAGE:$TAG"
for arg in "$@"; do
  case "$arg" in
    --latest) TAGS="$TAGS -t $IMAGE:latest" ;;
    --dev)    TAGS="$TAGS -t $IMAGE:dev" ;;
  esac
done

echo "🐳 Building MCP Server Docker image..."
echo "=================================="

# Build with BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build \
  --progress=plain \
  $TAGS \
  .

echo ""
echo "✅ Build complete!"
echo "   Tagged: $IMAGE:$TAG"
for arg in "$@"; do
  case "$arg" in
    --latest) echo "   Tagged: $IMAGE:latest" ;;
    --dev)    echo "   Tagged: $IMAGE:dev" ;;
  esac
done
echo ""
echo "To run the server:"
echo "  docker-compose up -d"
