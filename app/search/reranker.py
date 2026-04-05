import asyncio
from sentence_transformers import CrossEncoder

_model: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
    return _model


async def rerank(
    query: str,
    candidates: list[tuple[str, str]],
    top_k: int = 5,
) -> list[tuple[str, float]]:
    """
    Rerank candidates. Returns [(chunk_id, score), ...] top_k sorted.
    Runs in thread pool to not block async loop.
    """
    if not candidates:
        return []

    pairs = [[query, text] for _, text in candidates]
    reranker = get_reranker()

    scores = await asyncio.to_thread(reranker.predict, pairs)

    ranked = sorted(
        zip([cid for cid, _ in candidates], scores),
        key=lambda x: x[1],
        reverse=True,
    )
    return [(cid, float(score)) for cid, score in ranked[:top_k]]
