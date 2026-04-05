"""MCP server that exposes product identification via vector similarity search."""

import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from src.server import mcp
from src.server.auth import verify_token
from src.server.permissions import set_user
from src.server.routes.admin import router as admin_router
from src.vectorstore.manager import initialize_vectorstore
import src.server.tools

# Knowledge API routes
from app.routes.upload_file import router as upload_file_router
from app.routes.add_url import router as add_url_router
from app.routes.add_urls_bulk import router as add_urls_bulk_router
from app.routes.upload_sitemap import router as upload_sitemap_router
from app.routes.reindex import router as reindex_router
from app.routes.sources import router as sources_router
from app.routes.search_test import router as search_test_router
from app.vector.chroma import ensure_collection
from app.search.reranker import get_reranker


class AuthMiddleware:
    """Raw ASGI middleware for auth — compatible with SSE/streaming responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            try:
                user = verify_token(auth)
                set_user(user)
            except Exception as e:
                status = getattr(e, "status_code", 401)
                detail = getattr(e, "detail", str(e))
                body = json.dumps({"error": detail}).encode()
                await send({
                    "type": "http.response.start",
                    "status": status,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


# Initialize products vectorstore (synchronous — uses HTTP ChromaDB client)
vectorstore = initialize_vectorstore()

# Create MCP app with CORS for Claude Code compatibility
mcp_app = mcp.http_app(
    path="/",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
    transport="sse"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure company_knowledge ChromaDB collection exists
    await ensure_collection()
    # Pre-load cross-encoder reranker model into memory
    get_reranker()
    # Run MCP app lifecycle (required for FastMCP SSE transport)
    async with mcp_app.lifespan(app):
        yield


api = FastAPI(
    title="T4A MCP + Knowledge API",
    description="MCP server with product tools and company knowledge base",
    lifespan=lifespan,
)

api.add_middleware(AuthMiddleware)

# Existing admin routes (product reindex)
api.include_router(admin_router)

# Knowledge API admin routes
api.include_router(upload_file_router)
api.include_router(add_url_router)
api.include_router(add_urls_bulk_router)
api.include_router(upload_sitemap_router)
api.include_router(reindex_router)
api.include_router(sources_router)
api.include_router(search_test_router)


@api.get("/admin-ui", include_in_schema=False)
def admin_ui():
    return FileResponse("app/static/admin.html")


@api.get("/")
def root():
    return {
        "service": "T4A MCP + Knowledge API",
        "mcp_endpoint": "/mcp",
        "health_check": "/health",
        "knowledge_admin": "/admin/sources",
    }


@api.get("/health")
async def health():
    checks: dict[str, str] = {}
    checks["vectorstore"] = "ok" if vectorstore else "not_loaded"

    # Check ChromaDB
    try:
        from app.vector.chroma import get_collection
        col = get_collection()
        col.count()
        checks["chromadb"] = "ok"
    except Exception as e:
        checks["chromadb"] = f"error: {e}"

    # Check MongoDB
    try:
        from app.db.mongo import get_sources_col
        col = get_sources_col()
        await col.database.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {e}"

    all_ok = all(v in ("ok", "not_loaded") for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", **checks}


api.mount("/mcp", mcp_app)

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000, log_level="debug")
