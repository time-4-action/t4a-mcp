from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.vector.chroma import delete_points, get_collection
from app.pipeline.ingester import ingest_source, full_bm25_rebuild

router = APIRouter()


def _format_source(doc: dict) -> dict:
    """Serialize a MongoDB source document for API response."""
    return {
        "id": str(doc["_id"]),
        "type": doc.get("type"),
        "label": doc.get("label"),
        "status": doc.get("status"),
        "url": doc.get("url"),
        "originalName": doc.get("originalName"),
        "mimeType": doc.get("mimeType"),
        "totalChunks": doc.get("totalChunks", 0),
        "contentHash": doc.get("contentHash"),
        "lastIndexed": doc.get("lastIndexed"),
        "errorMessage": doc.get("errorMessage"),
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),
        "isSitemapRoot": doc.get("isSitemapRoot", False),
        "sitemapChildCount": doc.get("sitemapChildCount"),
        "parentSitemapId": str(doc["parentSitemapId"]) if doc.get("parentSitemapId") else None,
    }


@router.get("/admin/sources")
async def list_sources(
    type: str = None,
    status: str = None,
    page: int = 1,
    limit: int = 50,
    _: str = Depends(require_api_key),
):
    col = get_sources_col()
    query = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status

    total = await col.count_documents(query)
    docs = await col.find(query).skip((page - 1) * limit).limit(limit).to_list(None)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "sources": [_format_source(d) for d in docs],
    }


@router.get("/admin/source/{source_id}")
async def get_source(source_id: str, _: str = Depends(require_api_key)):
    col = get_sources_col()
    try:
        doc = await col.find_one({"_id": ObjectId(source_id)})
    except Exception:
        raise HTTPException(400, "Invalid source ID")
    if not doc:
        raise HTTPException(404, "Source not found")
    return _format_source(doc)


@router.delete("/admin/source/{source_id}")
async def delete_source(source_id: str, _: str = Depends(require_api_key)):
    col = get_sources_col()
    try:
        doc = await col.find_one({"_id": ObjectId(source_id)})
    except Exception:
        raise HTTPException(400, "Invalid source ID")
    if not doc:
        raise HTTPException(404, "Source not found")

    all_ids = (
        doc.get("childChunkIds", [])
        + doc.get("parentChunkIds", [])
        + ([doc["summaryChunkId"]] if doc.get("summaryChunkId") else [])
    )
    await delete_points(all_ids)
    await col.delete_one({"_id": doc["_id"]})
    await full_bm25_rebuild()

    return {"deleted": True, "chunksRemoved": len(all_ids)}


@router.post("/admin/source/{source_id}/reindex")
async def reindex_single(source_id: str, _: str = Depends(require_api_key)):
    col = get_sources_col()
    try:
        doc = await col.find_one({"_id": ObjectId(source_id)})
    except Exception:
        raise HTTPException(400, "Invalid source ID")
    if not doc:
        raise HTTPException(404, "Source not found")

    updates = await ingest_source(source_doc=doc, force=True)
    updates["updatedAt"] = datetime.now(timezone.utc)
    await col.update_one({"_id": doc["_id"]}, {"$set": updates})
    await full_bm25_rebuild()

    return {"sourceId": source_id, **{k: v for k, v in updates.items() if k != "parentChunkMap"}}


@router.get("/admin/stats")
async def get_stats(_: str = Depends(require_api_key)):
    col = get_sources_col()

    # Aggregate counts by type and status
    by_type_cursor = col.aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}}}
    ])
    by_type = {doc["_id"]: doc["count"] async for doc in by_type_cursor if doc["_id"]}

    by_status_cursor = col.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ])
    by_status = {doc["_id"]: doc["count"] async for doc in by_status_cursor if doc["_id"]}

    total = await col.count_documents({})

    # Count total child chunks
    pipeline = [
        {"$match": {"status": "indexed"}},
        {"$project": {"chunkCount": {"$size": {"$ifNull": ["$childChunkIds", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$chunkCount"}}},
    ]
    agg = await col.aggregate(pipeline).to_list(1)
    total_child_chunks = agg[0]["total"] if agg else 0

    # Last reindex time
    last_doc = await col.find_one(
        {"lastIndexed": {"$exists": True}},
        sort=[("lastIndexed", -1)],
    )
    last_reindex = last_doc["lastIndexed"] if last_doc else None

    # ChromaDB chunk count
    try:
        chroma_count = get_collection().count()
    except Exception:
        chroma_count = 0

    return {
        "sources": {
            "total": total,
            "byType": by_type,
            "byStatus": by_status,
        },
        "chunks": {
            "totalChildChunks": total_child_chunks,
            "chromaDbCount": chroma_count,
        },
        "lastReindex": last_reindex,
    }
