import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source
import app.config as settings

router = APIRouter()


class UrlItem(BaseModel):
    url: HttpUrl
    label: str | None = None


class BulkUrlBody(BaseModel):
    urls: list[UrlItem]


@router.post("/admin/add-urls-bulk")
async def add_urls_bulk(body: BulkUrlBody, _: str = Depends(require_api_key)):
    col = get_sources_col()
    results = {"indexed": 0, "skipped": 0, "failed": 0, "sources": []}

    for item in body.urls:
        url_str = str(item.url)
        await asyncio.sleep(settings.CRAWL_DELAY_MS / 1000)
        try:
            existing = await col.find_one({"url": url_str})
            if existing:
                results["skipped"] += 1
                continue

            source_doc = {
                "_id": ObjectId(),
                "type": "url",
                "label": item.label or url_str,
                "url": url_str,
                "status": "pending",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
            await col.insert_one(source_doc)
            updates = await ingest_source(source_doc=source_doc)
            updates["updatedAt"] = datetime.now(timezone.utc)
            await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})

            results["indexed"] += 1
            results["sources"].append({
                "sourceId": str(source_doc["_id"]),
                "url": url_str,
                "status": updates.get("status"),
            })
        except Exception as e:
            results["failed"] += 1
            results["sources"].append({"url": url_str, "status": "error", "error": str(e)})

    return results
