from datetime import datetime, timezone

from app.db.mongo import get_sources_col
from app.pipeline.parser import parse_file, parse_url
from app.pipeline.chunker import build_parent_child_chunks
from app.pipeline.enricher import enrich_chunks_batch, generate_summary
from app.pipeline.embedder import embed_texts
from app.vector.chroma import upsert_points, delete_points, ensure_collection, get_points_by_ids
from app.search.bm25 import get_global_index, rebuild_global_index


async def ingest_source(
    *,
    source_doc: dict,
    force: bool = False,
) -> dict:
    """
    Full pipeline: parse → chunk → enrich → embed → store.
    Returns updated source fields to $set in MongoDB.
    """
    await ensure_collection()
    source_id = str(source_doc["_id"])
    label = source_doc.get("label", source_id)

    # 1. Parse
    if source_doc["type"] == "file":
        text, content_hash = await parse_file(source_doc["filePath"])
    else:
        text, content_hash = await parse_url(source_doc["url"])

    # 2. Skip if unchanged
    if not force and source_doc.get("contentHash") == content_hash:
        return {"status": "skipped"}

    # 3. Delete old vectors if reindexing
    old_child_ids = source_doc.get("childChunkIds", [])
    old_parent_ids = source_doc.get("parentChunkIds", [])
    old_summary_id = source_doc.get("summaryChunkId")
    all_old = old_child_ids + old_parent_ids + ([old_summary_id] if old_summary_id else [])
    await delete_points(all_old)

    # 4. Chunk (parent-child)
    parents, children = build_parent_child_chunks(
        text=text,
        source_id=source_id,
        source_label=label,
        source_type=source_doc["type"],
        source_url=source_doc.get("url"),
    )

    # 5. Enrich child chunks with Claude context
    enriched_texts = await enrich_chunks_batch(text, children, concurrency=5)

    # 6. Generate summary chunk
    summary_text = await generate_summary(text, label)
    summary_id = f"{source_id}_summary"

    # 7. Embed: children (enriched) + summary
    all_embed_texts = enriched_texts + [summary_text]
    all_embed_ids = [c.id for c in children] + [summary_id]
    embeddings = await embed_texts(all_embed_texts)

    # 8. Upsert into ChromaDB
    child_payloads = []
    for chunk, enriched in zip(children, enriched_texts):
        child_payloads.append({
            **chunk.metadata,
            "chunk_id": chunk.id,
            "text": enriched,
            "original_text": chunk.text,
            "chunk_type": "child",
        })

    summary_payload = {
        "source_id": source_id,
        "source_label": label,
        "source_type": source_doc["type"],
        "chunk_id": summary_id,
        "text": summary_text,
        "chunk_type": "summary",
    }
    if source_doc.get("url"):
        summary_payload["source_url"] = source_doc["url"]

    await upsert_points(
        ids=all_embed_ids,
        vectors=embeddings,
        payloads=child_payloads + [summary_payload],
    )

    # 9. Parent chunk map stored in MongoDB for context expansion during retrieval
    parent_map = {p.id: p.text for p in parents}

    return {
        "status": "indexed",
        "contentHash": content_hash,
        "childChunkIds": [c.id for c in children],
        "parentChunkIds": [p.id for p in parents],
        "summaryChunkId": summary_id,
        "totalChunks": len(children),
        "parentChunkMap": parent_map,
        "lastIndexed": datetime.now(timezone.utc),
    }


async def full_bm25_rebuild() -> int:
    """Rebuild global BM25 from all indexed sources in MongoDB. Returns doc count."""
    col = get_sources_col()
    sources = await col.find(
        {"status": "indexed", "childChunkIds": {"$exists": True}},
        {"childChunkIds": 1}
    ).to_list(None)

    all_ids = []
    all_texts = []

    for source in sources:
        ids = source.get("childChunkIds", [])
        if not ids:
            continue
        points = await get_points_by_ids(ids)
        for p in points:
            all_ids.append(p["payload"]["chunk_id"])
            all_texts.append(p["payload"].get("text", ""))

    rebuild_global_index(all_ids, all_texts)
    return len(all_ids)
