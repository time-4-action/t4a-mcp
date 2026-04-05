from bson import ObjectId

from app.pipeline.embedder import embed_query
from app.search.hybrid import hybrid_search
from app.search.reranker import rerank
from app.vector.chroma import get_points_by_ids
from app.db.mongo import get_sources_col
import app.config as settings


async def retrieve(
    query: str,
    top_k: int = None,
) -> list[dict]:
    """
    Full pipeline: embed → hybrid search → rerank → parent expansion.
    Returns list of result dicts with text, source info, scores.
    """
    top_k = top_k or settings.TOP_K_RERANK

    # 1. Embed query
    query_vector = await embed_query(query)

    # 2. Hybrid search → top-30 candidate IDs
    fused_results = await hybrid_search(
        query_text=query,
        query_vector=query_vector,
        top_k_fused=30,
    )

    if not fused_results:
        return []

    # 3. Fetch chunk texts from ChromaDB for reranking
    candidate_ids = [cid for cid, _ in fused_results]
    points = await get_points_by_ids(candidate_ids)
    id_to_point = {p["id"]: p for p in points}

    candidates = []
    for cid, _ in fused_results:
        point = id_to_point.get(cid)
        if point:
            text = point["payload"].get("text", "")
            candidates.append((cid, text))

    if not candidates:
        return []

    # 4. Rerank → top_k
    reranked = await rerank(query, candidates, top_k=top_k)

    # 5. Parent chunk expansion — batch-fetch all needed source docs in one query
    col = get_sources_col()

    # Collect unique source_ids that have a parent_id
    source_ids_needed: set[str] = set()
    for cid, _ in reranked:
        point = id_to_point.get(cid)
        if point:
            payload = point["payload"]
            if payload.get("parent_id") and payload.get("source_id"):
                source_ids_needed.add(payload["source_id"])

    source_docs: dict[str, dict] = {}
    if source_ids_needed:
        try:
            cursor = col.find(
                {"_id": {"$in": [ObjectId(sid) for sid in source_ids_needed]}},
                {"parentChunkMap": 1},
            )
            async for doc in cursor:
                source_docs[str(doc["_id"])] = doc
        except Exception:
            pass  # Fall back to child chunk text below

    results = []
    for rank, (cid, rerank_score) in enumerate(reranked, start=1):
        point = id_to_point.get(cid)
        if not point:
            continue

        payload = point["payload"]
        source_id = payload.get("source_id")
        parent_id = payload.get("parent_id")

        parent_text = payload.get("original_text", "")
        if parent_id and source_id:
            source_doc = source_docs.get(source_id)
            if source_doc and source_doc.get("parentChunkMap"):
                parent_text = source_doc["parentChunkMap"].get(parent_id, parent_text)

        results.append({
            "rank": rank,
            "chunk_id": cid,
            "rerank_score": rerank_score,
            "text": parent_text or payload.get("text", ""),
            "source_label": payload.get("source_label", ""),
            "source_url": payload.get("source_url", ""),
            "source_type": payload.get("source_type", ""),
            "source_id": source_id,
            "chunk_type": payload.get("chunk_type", ""),
        })

    return results
