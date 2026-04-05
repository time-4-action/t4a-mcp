import asyncio
from app.vector.chroma import search_dense
from app.search.bm25 import get_global_index
import app.config as settings


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    RRF formula: score(d) = Σ 1/(k + rank(d))
    k=60 is the standard default from the original RRF paper.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def hybrid_search(
    query_text: str,
    query_vector: list[float],
    top_k_dense: int = None,
    top_k_bm25: int = None,
    top_k_fused: int = 30,
) -> list[tuple[str, float]]:
    """
    Run dense + BM25 in parallel, fuse with RRF.
    Returns [(chunk_id, rrf_score), ...] — top_k_fused results.
    """
    top_k_dense = top_k_dense or settings.TOP_K_DENSE
    top_k_bm25 = top_k_bm25 or settings.TOP_K_BM25

    dense_results_raw, bm25_results = await asyncio.gather(
        search_dense(query_vector, top_k=top_k_dense),
        asyncio.to_thread(get_global_index().query, query_text, top_k_bm25),
    )

    dense_results = [(r[0], r[1]) for r in dense_results_raw]

    fused = reciprocal_rank_fusion([dense_results, bm25_results])
    return fused[:top_k_fused]
