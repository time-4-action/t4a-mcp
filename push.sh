#!/bin/bash
# Push MCP Server Docker image to registry

set -e

echo "🐳 Pushing MCP Server Docker image..."
echo "=================================="
echo ""

# Push latest tag
echo "Pushing etiamsi/t4a-mcp:latest..."
docker push etiamsi/t4a-mcp:latest

# Push timestamped tag if it exists
TIMESTAMPED_TAG=$(docker images etiamsi/t4a-mcp --format "{{.Tag}}" | grep -E '^[0-9]{8}-[0-9]{6}$' | head -n 1)
if [ -n "$TIMESTAMPED_TAG" ]; then
    echo ""
    echo "Pushing etiamsi/t4a-mcp:$TIMESTAMPED_TAG..."
    docker push etiamsi/t4a-mcp:$TIMESTAMPED_TAG
fi

echo ""
echo "✅ Push complete!"
echo ""
echo "Image(s) pushed to Docker Hub:"
echo "  etiamsi/t4a-mcp:latest"
if [ -n "$TIMESTAMPED_TAG" ]; then
    echo "  etiamsi/t4a-mcp:$TIMESTAMPED_TAG"
fi
echo ""
