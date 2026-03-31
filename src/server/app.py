"""MCP server that exposes product identification via vector similarity search."""

import json
import uvicorn
from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from src.server import mcp
from src.server.auth import verify_token
from src.server.permissions import set_user
from src.server.routes.admin import router as admin_router
from src.vectorstore.manager import initialize_vectorstore
import src.server.tools


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

# Initialize vectorstore
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

api = FastAPI(
    title="Product Identifier API",
    description="MCP server with product identification and pricing tools",
    lifespan=mcp_app.lifespan,
)

api.add_middleware(AuthMiddleware)
api.include_router(admin_router)


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
    uvicorn.run(api, host="0.0.0.0", port=8000, log_level="debug")
