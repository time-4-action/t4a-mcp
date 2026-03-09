"""MCP server that exposes product identification via vector similarity search."""

import uvicorn
from fastapi import FastAPI, Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from src.server import mcp
from src.server.auth import verify_token
from src.server.permissions import set_user
from src.vectorstore.manager import initialize_vectorstore
import src.server.tools


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            try:
                user = verify_token(request.headers.get("authorization"))
                set_user(user)
            except Exception as e:
                status = getattr(e, "status_code", 401)
                detail = getattr(e, "detail", str(e))
                return JSONResponse({"error": detail}, status_code=status)
        return await call_next(request)

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
