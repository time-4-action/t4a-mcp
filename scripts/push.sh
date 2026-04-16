#!/bin/bash
# Push MCP Server Docker image to registry
# Usage: ./push.sh [--latest] [--dev]

set -e

IMAGE="time4action/t4a-mcp"

echo "🐳 Pushing MCP Server Docker image..."
echo "=================================="
echo ""

# Find the most recent timestamped tag
TIMESTAMPED_TAG=$(docker images $IMAGE --format "{{.Tag}}" | grep -E '^[0-9]{8}-[0-9]{6}$' | head -n 1)

if [ -n "$TIMESTAMPED_TAG" ]; then
    echo "Pushing $IMAGE:$TIMESTAMPED_TAG..."
    docker push $IMAGE:$TIMESTAMPED_TAG
else
    echo "⚠️  No timestamped tag found. Build first with ./build.sh"
    exit 1
fi

for arg in "$@"; do
  case "$arg" in
    --latest)
      echo ""
      echo "Pushing $IMAGE:latest..."
      docker push $IMAGE:latest
      ;;
    --dev)
      echo ""
      echo "Pushing $IMAGE:dev..."
      docker push $IMAGE:dev
      ;;
  esac
done

echo ""
echo "✅ Push complete!"
echo ""
echo "Image(s) pushed to Docker Hub:"
echo "  $IMAGE:$TIMESTAMPED_TAG"
for arg in "$@"; do
  case "$arg" in
    --latest) echo "  $IMAGE:latest" ;;
    --dev)    echo "  $IMAGE:dev" ;;
  esac
done
echo ""
