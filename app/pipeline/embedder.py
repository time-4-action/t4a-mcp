from openai import AsyncOpenAI
import app.config as settings

_client: AsyncOpenAI | None = None
MODEL = "text-embedding-3-large"
DIMENSIONS = 3072


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Handles batching automatically."""
    all_embeddings = []
    batch_size = settings.EMBED_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await get_client().embeddings.create(
            model=MODEL,
            input=batch,
            dimensions=DIMENSIONS,
        )
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    response = await get_client().embeddings.create(
        model=MODEL,
        input=[text],
        dimensions=DIMENSIONS,
    )
    return response.data[0].embedding
