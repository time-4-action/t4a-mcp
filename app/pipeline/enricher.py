import asyncio
from anthropic import AsyncAnthropic
import app.config as settings
from app.pipeline.chunker import Chunk

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


CONTEXT_PROMPT = """\
<document>
{doc_text}
</document>

Here is a chunk from the document:
<chunk>
{chunk_text}
</chunk>

In 1-2 sentences, explain what this chunk is about within the context of the document.
Write only the contextual description, nothing else. No preamble."""

SUMMARY_PROMPT = """\
<document>
{doc_text}
</document>

Write a 150-200 word summary of this document. Include:
- What it is (type of document, source)
- Main topics covered
- Key facts, names, or values mentioned

Write only the summary, no preamble."""


async def enrich_chunk(doc_text: str, chunk_text: str) -> str:
    """Returns enriched text: context_prefix + original chunk."""
    resp = await get_client().messages.create(
        model=settings.ENRICH_MODEL,
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": CONTEXT_PROMPT.format(
                doc_text=doc_text[:8000],
                chunk_text=chunk_text,
            )
        }]
    )
    context = resp.content[0].text.strip()
    return f"{context}\n\n{chunk_text}"


async def enrich_chunks_batch(
    doc_text: str,
    chunks: list[Chunk],
    concurrency: int = 5,
) -> list[str]:
    """Enrich all child chunks concurrently (rate-limited)."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _enrich(chunk: Chunk) -> str:
        async with semaphore:
            return await enrich_chunk(doc_text, chunk.text)

    return await asyncio.gather(*[_enrich(c) for c in chunks])


async def generate_summary(doc_text: str, source_label: str) -> str:
    """Generate a document-level summary chunk for embedding."""
    resp = await get_client().messages.create(
        model=settings.ENRICH_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(doc_text=doc_text[:12000])
        }]
    )
    return f"[SUMMARY: {source_label}]\n\n{resp.content[0].text.strip()}"
