import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.parser import parse_sitemap_xml
from app.pipeline.ingester import ingest_source, full_bm25_rebuild
import app.config as settings

router = APIRouter()


@router.post("/admin/upload-sitemap")
async def upload_sitemap(
    file: UploadFile = File(...),
    base_label: str = Form(""),
    crawl_now: bool = Form(True),
    _: str = Depends(require_api_key),
):
    content = (await file.read()).decode("utf-8", errors="ignore")
    urls = await parse_sitemap_xml(content)
    urls = list(dict.fromkeys(urls))[:settings.MAX_SITEMAP_URLS]

    col = get_sources_col()

    sitemap_root_id = ObjectId()
    await col.insert_one({
        "_id": sitemap_root_id,
        "type": "sitemap_root",
        "label": base_label or file.filename,
        "isSitemapRoot": True,
        "sitemapChildCount": len(urls),
        "status": "indexed",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })

    result = {
        "sitemapId": str(sitemap_root_id),
        "urlsFound": len(urls),
        "indexed": 0,
        "skipped": 0,
        "failed": 0,
        "sources": [],
    }

    if not crawl_now:
        return result

    for url in urls:
        await asyncio.sleep(settings.CRAWL_DELAY_MS / 1000)
        try:
            existing = await col.find_one({"url": url})
            if existing:
                result["skipped"] += 1
                continue

            source_doc = {
                "_id": ObjectId(),
                "type": "sitemap_child",
                "label": url,
                "url": url,
                "parentSitemapId": sitemap_root_id,
                "status": "pending",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
            await col.insert_one(source_doc)
            updates = await ingest_source(source_doc=source_doc)
            updates["updatedAt"] = datetime.now(timezone.utc)
            await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})

            result["indexed"] += 1
            result["sources"].append({
                "sourceId": str(source_doc["_id"]),
                "url": url,
                "status": updates.get("status"),
                "totalChunks": updates.get("totalChunks", 0),
            })
        except Exception as e:
            result["failed"] += 1
            result["sources"].append({"url": url, "status": "error", "error": str(e)})

    await full_bm25_rebuild()
    return result
