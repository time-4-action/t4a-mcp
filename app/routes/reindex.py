import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source, full_bm25_rebuild

router = APIRouter()


@router.post("/admin/reindex-company-data")
async def reindex_all(_: str = Depends(require_api_key)):
    t0 = time.time()
    col = get_sources_col()
    sources = await col.find(
        {"type": {"$in": ["file", "url", "sitemap_child"]}}
    ).to_list(None)

    stats = {"total": len(sources), "reindexed": 0, "unchanged": 0, "failed": 0}

    for source in sources:
        await asyncio.sleep(0.1)
        try:
            updates = await ingest_source(source_doc=source)
            status = updates.get("status")
            if status == "skipped":
                stats["unchanged"] += 1
            else:
                updates["updatedAt"] = datetime.now(timezone.utc)
                await col.update_one({"_id": source["_id"]}, {"$set": updates})
                stats["reindexed"] += 1
        except Exception as e:
            stats["failed"] += 1
            await col.update_one(
                {"_id": source["_id"]},
                {"$set": {"status": "error", "errorMessage": str(e)}}
            )

    total_bm25_docs = await full_bm25_rebuild()

    stats["durationMs"] = int((time.time() - t0) * 1000)
    stats["bm25DocumentCount"] = total_bm25_docs
    return stats
