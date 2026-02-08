"""MCP server that exposes product identification via vector similarity search."""

import uvicorn
from fastapi import FastAPI

from mcp_server import mcp
from mcp_server.vectorstore import vectorstore
import mcp_server.tools

mcp_app = mcp.http_app(path="/")

api = FastAPI(
    title="Product Identifier API",
    description="MCP server with product identification and pricing tools",
    lifespan=mcp_app.lifespan,
)


@api.get("/")
def root():
    return {
        "service": "Product Identifier API",
        "mcp_endpoint": "/mcp",
        "health_check": "/health",
    }


@api.get("/health")
def health():
    return {"status": "ok", "vectorstore": "initialized" if vectorstore else "not_loaded"}


api.mount("/mcp", mcp_app)

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
