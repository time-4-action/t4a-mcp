from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source

router = APIRouter()


class AddUrlBody(BaseModel):
    url: HttpUrl
    label: str | None = None


@router.post("/admin/add-url")
async def add_url(body: AddUrlBody, _: str = Depends(require_api_key)):
    url_str = str(body.url)
    col = get_sources_col()

    existing = await col.find_one({"url": url_str})
    if existing:
        raise HTTPException(409, f"URL already registered: {existing['_id']}")

    source_doc = {
        "_id": ObjectId(),
        "type": "url",
        "label": body.label or url_str,
        "url": url_str,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    await col.insert_one(source_doc)

    try:
        updates = await ingest_source(source_doc=source_doc)
        updates["updatedAt"] = datetime.now(timezone.utc)
        await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})
    except Exception as e:
        await col.update_one(
            {"_id": source_doc["_id"]},
            {"$set": {"status": "error", "errorMessage": str(e)}}
        )
        raise HTTPException(500, f"Ingestion failed: {e}")

    return {
        "sourceId": str(source_doc["_id"]),
        "url": url_str,
        "status": updates.get("status"),
        "totalChunks": updates.get("totalChunks", 0),
    }
