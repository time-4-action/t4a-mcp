import asyncio
import chromadb
import app.config as settings

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def ensure_collection():
    """Called at startup — creates collection if it doesn't exist."""
    await asyncio.to_thread(get_collection)


async def upsert_points(
    ids: list[str],
    vectors: list[list[float]],
    payloads: list[dict],
):
    """Upsert chunks into ChromaDB in batches."""
    col = get_collection()
    batch_size = 100
    metadatas = [_flatten_payload(p) for p in payloads]
    documents = [p.get("text", "") for p in payloads]

    def _upsert_batch(i):
        col.upsert(
            ids=ids[i : i + batch_size],
            embeddings=vectors[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    for i in range(0, len(ids), batch_size):
        await asyncio.to_thread(_upsert_batch, i)


async def delete_points(ids: list[str]):
    """Delete chunks by ID."""
    if not ids:
        return
    col = get_collection()
    await asyncio.to_thread(col.delete, ids=ids)


async def search_dense(
    query_vector: list[float],
    top_k: int = 20,
    filter_source_id: str = None,
) -> list[tuple[str, float, dict]]:
    """
    Dense cosine search. Returns [(chunk_id, score, metadata), ...].
    ChromaDB returns distances; we convert to similarity (1 - distance).
    """
    col = get_collection()
    where = {"source_id": filter_source_id} if filter_source_id else None

    def _query():
        count = col.count()
        if count == 0:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}
        kwargs = {
            "query_embeddings": [query_vector],
            "n_results": min(top_k, count),
            "include": ["metadatas", "documents", "distances"],
        }
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    results = await asyncio.to_thread(_query)

    output = []
    if results["ids"] and results["ids"][0]:
        for chunk_id, distance, metadata in zip(
            results["ids"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            score = 1.0 - distance
            output.append((chunk_id, score, metadata))

    return output


async def get_points_by_ids(ids: list[str]) -> list[dict]:
    """Fetch full metadata + documents for a list of chunk IDs."""
    if not ids:
        return []
    col = get_collection()

    def _get():
        return col.get(ids=ids, include=["metadatas", "documents"])

    results = await asyncio.to_thread(_get)

    output = []
    for chunk_id, metadata, document in zip(
        results["ids"],
        results["metadatas"],
        results["documents"],
    ):
        payload = dict(metadata)
        payload["text"] = document
        output.append({"id": chunk_id, "payload": payload})

    return output


def _flatten_payload(payload: dict) -> dict:
    """ChromaDB metadata must be flat (str/int/float/bool values only)."""
    flat = {}
    for k, v in payload.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            flat[k] = v if v is not None else ""
        else:
            flat[k] = str(v)
    return flat
