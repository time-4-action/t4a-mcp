"""Read-only knowledge base API for the T4A agent (t4a-agent).

Guarded by AGENT_READ_KEY only: the admin key does not open these routes, and
this key opens nothing else (/admin/* and /mcp keep their own auth).
"""

import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

import app.config as settings
from app.db.mongo import get_sources_col

MAX_TEXT_CHARS = 4000

router = APIRouter(prefix="/agent/knowledge", tags=["agent"])

_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def require_agent_key(key: str | None = Security(_key_header)) -> None:
    expected = settings.AGENT_READ_KEY
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Agent API is not configured")
    if not key or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing x-api-key header")


class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


async def _retrieve(query: str, top_k: int) -> list[dict]:
    # Imported lazily, like the company_knowledge MCP tool: app.retrieval pulls in
    # the embedder and the cross-encoder.
    from app.retrieval import retrieve

    return await retrieve(query, top_k=top_k)


@router.post("/search", dependencies=[Depends(require_agent_key)])
async def search(body: SearchBody):
    results = await _retrieve(body.query, body.top_k)
    return {
        "results": [
            {
                "source_id": r.get("source_id"),
                "source_title": r.get("source_label") or None,
                "source_type": r.get("source_type") or None,
                "source_url": r.get("source_url") or None,
                "text": (r.get("text") or "")[:MAX_TEXT_CHARS],
                "score": r.get("rerank_score"),
            }
            for r in results
        ]
    }


def _iso_utc(value) -> str | None:
    # Motor returns naive UTC datetimes; send an unambiguous ISO 8601 string.
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/sources", dependencies=[Depends(require_agent_key)])
async def sources():
    col = get_sources_col()
    projection = {"label": 1, "originalName": 1, "type": 1, "url": 1, "totalChunks": 1, "createdAt": 1}
    docs = await col.find({}, projection).sort("createdAt", -1).to_list(None)
    items = [
        {
            "source_id": str(d["_id"]),
            "title": d.get("label") or d.get("originalName") or d.get("url"),
            "type": d.get("type"),
            "url": d.get("url"),
            "chunks": d.get("totalChunks", 0),
            "created_at": _iso_utc(d.get("createdAt")),
        }
        for d in docs
    ]
    return {"total": len(items), "items": items}
