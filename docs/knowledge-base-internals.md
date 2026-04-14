# T4A Company Knowledge Base — Full Implementation Guide
### State-of-the-art RAG pipeline · Early 2026

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Vector Store — ChromaDB](#2-vector-store--chromadb)
3. [Full Tech Stack](#3-full-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Environment & Dependencies](#5-environment--dependencies)
6. [MongoDB Schema](#6-mongodb-schema)
7. [Core Pipeline Implementation](#7-core-pipeline-implementation)
   - [Parser](#71-parser)
   - [Parent-Child Chunker](#72-parent-child-chunker)
   - [Claude Contextual Enrichment](#73-claude-contextual-enrichment)
   - [Embedder (OpenAI)](#74-embedder-openai)
   - [BM25 Index](#75-bm25-index)
   - [ChromaDB Store](#76-chromadb-store)
   - [Ingester Orchestrator](#77-ingester-orchestrator)
8. [Retrieval Pipeline](#8-retrieval-pipeline)
   - [Hybrid Search (Dense + BM25 + RRF)](#81-hybrid-search-dense--bm25--rrf)
   - [Reranker](#82-reranker)
   - [Full Retrieval Chain](#83-full-retrieval-chain)
9. [Admin API — All Endpoints](#9-admin-api--all-endpoints)
   - [Auth middleware](#91-auth-middleware)
   - [POST /admin/upload-file](#92-post-adminupload-file)
   - [POST /admin/add-url](#93-post-adminadd-url)
   - [POST /admin/add-urls-bulk](#94-post-adminadd-urls-bulk)
   - [POST /admin/upload-sitemap](#95-post-adminupload-sitemap)
   - [POST /admin/reindex-company-data](#96-post-adminreindex-company-data)
   - [GET /admin/sources](#97-get-adminsources)
   - [GET /admin/source/:id](#98-get-adminsourceid)
   - [DELETE /admin/source/:id](#99-delete-adminsourceid)
   - [POST /admin/source/:id/reindex](#910-post-adminsourceidreindex)
   - [GET /admin/stats](#911-get-adminstats)
   - [POST /admin/search-test](#912-post-adminsearch-test)
10. [FastAPI App Entry Point](#10-fastapi-app-entry-point)
11. [MCP Tool — company_knowledge](#11-mcp-tool--company_knowledge)
12. [Docker Setup](#12-docker-setup)
13. [nginx Config](#13-nginx-config)
14. [Migration from ChromaDB](#14-migration-from-chromadb)
15. [Operational Runbook](#15-operational-runbook)

---

## 1. Architecture Overview

### Indexing Pipeline

```
Raw Source (file / URL / sitemap)
         │
         ▼
   [1. Parse] ──── unstructured, trafilatura
         │
         ▼
   [2. Parent-Child Chunking]
      parent: ~800 tokens  (sent to LLM for context)
      child:  ~200 tokens  (embedded for precise retrieval)
         │
         ▼
   [3. Claude Enrichment] ──── Haiku 3.5 (cheap)
      Prepend situational context to each child chunk
      Generate document-level summary chunk
         │
         ▼
   [4. Embed child chunks] ──── OpenAI text-embedding-3-large
         │
         ├──────────────────────────────────┐
         ▼                                  ▼
   [5a. ChromaDB]                     [5b. BM25 index]
   dense vectors                      keyword index
   (per source collection)            (serialized to MongoDB)
         │                                  │
         └──────────────────────────────────┘
         │
         ▼
   [MongoDB: knowledge_sources]
   metadata · hashes · chunk IDs · BM25 state
```

### Query / Retrieval Pipeline

```
Agent query: "What are our shipping policies?"
         │
         ▼
   [1. Embed query] ──── text-embedding-3-large
         │
         ├─────────────────────────────────────────────┐
         ▼                                             ▼
   [2a. ChromaDB dense search]              [2b. BM25 keyword search]
       top-20 chunks                             top-20 chunks
         │                                             │
         └─────────────────┬───────────────────────────┘
                           ▼
                  [3. RRF Fusion]
                  merge + deduplicate
                  → top-30 candidates
                           │
                           ▼
                  [4. Cross-encoder Reranker]
                  MiniLM reranks top-30
                  → top-5 best chunks
                           │
                           ▼
                  [5. Parent chunk fetch]
                  swap child chunks → parent chunks
                  → richer context to LLM
                           │
                           ▼
                  [6. Return to agent]
                  passages + source attribution
```

---

## 2. Vector Store — ChromaDB

We use ChromaDB as the vector store — it's already in your stack, simple to run in Docker, and perfectly capable for this pipeline. The hybrid search layer (BM25 + RRF + reranker) is implemented **on top of** ChromaDB in application code, so we don't need Qdrant's native hybrid support.

| Component | Approach |
|---|---|
| Dense search | ChromaDB cosine similarity |
| Keyword search | BM25 index in app layer (`rank_bm25`) |
| Fusion | RRF in app layer |
| Reranking | Cross-encoder in app layer |

> **Upgrade path:** If you outgrow ChromaDB (millions of chunks, sub-50ms latency requirements), swap `app/vector/chroma.py` for a Qdrant client — the rest of the pipeline stays identical.

---

## 3. Full Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| API | FastAPI + uvicorn | Admin endpoints, async |
| Parsing | `unstructured[pdf,docx,xlsx]` | File → text |
| Web scraping | `trafilatura` + `httpx` | URL → clean text |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | Parent-child splits |
| LLM enrichment | Anthropic Claude Haiku 3.5 | Contextual chunk wrapping |
| Embeddings | OpenAI `text-embedding-3-large` | Dense vectors |
| Keyword index | `rank_bm25` (BM25Okapi) | Sparse/keyword search |
| Vector store | ChromaDB | Dense search (self-hosted Docker) |
| Fusion | Custom RRF (k=60) | Merge dense + BM25 results |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Re-score top candidates |
| Metadata | MongoDB `t4a` db | Source tracking, hashes |
| Auth | `x-api-key` header | All admin routes |
| MCP | FastMCP | Expose tool to AI agents |

---

## 4. Project Structure

```
t4a-knowledge/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings from .env
│   ├── auth.py                    # x-api-key dependency
│   ├── db/
│   │   └── mongo.py               # Motor async MongoDB client
│   ├── vector/
│   │   └── chroma.py              # ChromaDB client + helpers
│   ├── search/
│   │   ├── bm25.py                # BM25 index build/query/persist
│   │   ├── hybrid.py              # RRF fusion logic
│   │   └── reranker.py            # Cross-encoder reranker
│   ├── pipeline/
│   │   ├── parser.py              # File + URL → raw text
│   │   ├── chunker.py             # Parent-child chunking
│   │   ├── enricher.py            # Claude contextual enrichment
│   │   ├── embedder.py            # OpenAI embeddings
│   │   └── ingester.py            # Full orchestration
│   ├── routes/
│   │   ├── upload_file.py
│   │   ├── add_url.py
│   │   ├── add_urls_bulk.py
│   │   ├── upload_sitemap.py
│   │   ├── reindex.py
│   │   ├── sources.py
│   │   └── search_test.py
│   └── mcp/
│       └── tool.py                # MCP company_knowledge tool
├── uploads/
├── bm25_indexes/                  # Persisted BM25 state per source
├── .env
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 5. Environment & Dependencies

### `.env`
```dotenv
# MongoDB (existing)
MONGO_URI=mongodb://t4a:pass@194.28.111.245:27017/
MONGO_DB_NAME=t4a

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=company_knowledge

# OpenAI (embeddings)
OPENAI_API_KEY=sk-...

# Anthropic (enrichment)
ANTHROPIC_API_KEY=sk-ant-...
ENRICH_MODEL=claude-haiku-4-5-20251001

# Admin auth
ADMIN_API_KEY=your-strong-secret-here

# Storage
UPLOAD_DIR=/app/uploads
BM25_DIR=/app/bm25_indexes

# Crawling
CRAWL_DELAY_MS=500
MAX_SITEMAP_URLS=500

# Pipeline tuning
PARENT_CHUNK_SIZE=800
PARENT_CHUNK_OVERLAP=100
CHILD_CHUNK_SIZE=200
CHILD_CHUNK_OVERLAP=20
EMBED_BATCH_SIZE=100
TOP_K_DENSE=20
TOP_K_BM25=20
TOP_K_RERANK=5
```

### `requirements.txt`
```
fastapi>=0.115.0
uvicorn[standard]
python-multipart
httpx
motor                            # async MongoDB
chromadb>=0.5.0
openai>=1.30.0
anthropic>=0.28.0
langchain-text-splitters
unstructured[pdf,docx,xlsx]
trafilatura
rank_bm25
sentence-transformers            # cross-encoder reranker
torch --index-url https://download.pytorch.org/whl/cpu
python-dotenv
aiofiles
pickle5; python_version < "3.8"
```

> **Note on torch:** The reranker (`sentence-transformers`) needs torch. For CPU-only Docker use the `--index-url` above — much smaller image. The reranker runs fast on CPU (50–100ms for 30 docs).

---

## 6. MongoDB Schema

### Collection: `knowledge_sources`

```js
{
  _id: ObjectId,

  // Source identity
  type: "file" | "url" | "sitemap_child",
  label: String,                      // human display name
  status: "pending" | "indexed" | "error" | "skipped",
  errorMessage: String,               // set on error

  // File-specific
  originalName: String,
  filePath: String,
  mimeType: String,

  // URL-specific
  url: String,
  parentSitemapId: ObjectId,          // set if from sitemap

  // Sitemap tracking
  isSitemapRoot: Boolean,             // true for the sitemap itself
  sitemapChildCount: Number,

  // Indexing state
  contentHash: String,               // SHA-256 of raw text — change detection
  lastIndexed: ISODate,

  // Chunk tracking
  parentChunkIds: [String],          // ChromaDB IDs for parent chunks
  childChunkIds: [String],           // ChromaDB IDs for child chunks
  summaryChunkId: String,            // ChromaDB ID for doc summary chunk
  totalChunks: Number,

  // BM25
  bm25IndexPath: String,             // path to serialized BM25 pickle

  createdAt: ISODate,
  updatedAt: ISODate
}
```

### Collection: `knowledge_bm25_global`

Stores the **global** BM25 index (across all sources) that gets rebuilt on reindex:

```js
{
  _id: ObjectId,
  indexPath: String,                 // path to serialized global BM25
  totalDocuments: Number,
  lastBuilt: ISODate
}
```

---

## 7. Core Pipeline Implementation

### 7.1 Parser

`app/pipeline/parser.py`

```python
import hashlib
import httpx
import trafilatura
from pathlib import Path
from unstructured.partition.auto import partition


async def parse_file(file_path: str) -> tuple[str, str]:
    """Returns (text, content_hash)"""
    elements = partition(filename=file_path)
    text = "\n\n".join(str(e) for e in elements if str(e).strip())
    return text, _hash(text)


async def parse_url(url: str) -> tuple[str, str]:
    """Fetch URL, extract clean text. Returns (text, content_hash)"""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "T4A-KnowledgeBot/1.0"})
        resp.raise_for_status()
    text = trafilatura.extract(
        resp.text,
        include_tables=True,
        include_links=False,
        favor_recall=True,
        no_fallback=False,
    ) or ""
    if not text.strip():
        raise ValueError(f"No extractable content at {url}")
    return text, _hash(text)


async def parse_sitemap_xml(content: str) -> list[str]:
    """Extract all <loc> URLs from sitemap XML (handles sitemapindex + urlset)."""
    import xml.etree.ElementTree as ET
    NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.fromstring(content)
    urls = []
    # Sitemap index — nested sitemaps
    for loc in root.findall(f"{{{NS}}}sitemap/{{{NS}}}loc"):
        urls.append(loc.text.strip())
    # Regular urlset
    for loc in root.findall(f"{{{NS}}}url/{{{NS}}}loc"):
        urls.append(loc.text.strip())
    return urls


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
```

---

### 7.2 Parent-Child Chunker

`app/pipeline/chunker.py`

The core idea: embed **small chunks** (precise retrieval), but when retrieved → return the **parent chunk** (rich context for LLM).

```python
import uuid
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


@dataclass
class Chunk:
    id: str
    text: str
    parent_id: str | None    # None if this IS the parent
    is_parent: bool
    index: int               # position in document
    metadata: dict


def build_parent_child_chunks(
    text: str,
    source_id: str,
    source_label: str,
    source_type: str,
    source_url: str = None,
) -> tuple[list[Chunk], list[Chunk]]:
    """
    Returns (parent_chunks, child_chunks).
    Each child knows its parent_id.
    Each parent knows its index for context window ordering.
    """
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.PARENT_CHUNK_SIZE,
        chunk_overlap=settings.PARENT_CHUNK_OVERLAP,
        length_function=len,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHILD_CHUNK_SIZE,
        chunk_overlap=settings.CHILD_CHUNK_OVERLAP,
        length_function=len,
    )

    parent_texts = parent_splitter.split_text(text)
    parents = []
    children = []

    base_meta = {
        "source_id": source_id,
        "source_label": source_label,
        "source_type": source_type,
    }
    if source_url:
        base_meta["source_url"] = source_url

    for p_idx, p_text in enumerate(parent_texts):
        p_id = f"{source_id}_p{p_idx}"
        parents.append(Chunk(
            id=p_id,
            text=p_text,
            parent_id=None,
            is_parent=True,
            index=p_idx,
            metadata={**base_meta, "chunk_type": "parent", "parent_index": p_idx},
        ))

        child_texts = child_splitter.split_text(p_text)
        for c_idx, c_text in enumerate(child_texts):
            c_id = f"{source_id}_p{p_idx}_c{c_idx}"
            children.append(Chunk(
                id=c_id,
                text=c_text,
                parent_id=p_id,
                is_parent=False,
                index=c_idx,
                metadata={
                    **base_meta,
                    "chunk_type": "child",
                    "parent_id": p_id,
                    "parent_index": p_idx,
                    "child_index": c_idx,
                },
            ))

    return parents, children
```

---

### 7.3 Claude Contextual Enrichment

`app/pipeline/enricher.py`

Prepends a short situational context to every child chunk before embedding.
Also generates a document-level summary chunk.

```python
import asyncio
from anthropic import AsyncAnthropic
from app.config import settings
from app.pipeline.chunker import Chunk

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

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
    resp = await client.messages.create(
        model=settings.ENRICH_MODEL,
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": CONTEXT_PROMPT.format(
                doc_text=doc_text[:8000],    # truncate for cost
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
    """Generate a document-level summary for embedding as an extra chunk."""
    resp = await client.messages.create(
        model=settings.ENRICH_MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(doc_text=doc_text[:12000])
        }]
    )
    return f"[SUMMARY: {source_label}]\n\n{resp.content[0].text.strip()}"
```

---

### 7.4 Embedder (OpenAI)

`app/pipeline/embedder.py`

```python
from openai import AsyncOpenAI
from app.config import settings

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = "text-embedding-3-large"
DIMENSIONS = 3072  # full dimensions for max quality


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Handles batching automatically."""
    all_embeddings = []
    batch_size = settings.EMBED_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await _client.embeddings.create(
            model=MODEL,
            input=batch,
            dimensions=DIMENSIONS,
        )
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    response = await _client.embeddings.create(
        model=MODEL,
        input=[text],
        dimensions=DIMENSIONS,
    )
    return response.data[0].embedding
```

---

### 7.5 BM25 Index

`app/search/bm25.py`

BM25 is built over child chunk texts and serialized per-source. A global index is rebuilt on reindex.

```python
import os
import pickle
from rank_bm25 import BM25Okapi
from app.config import settings


def tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer. Good enough for BM25."""
    return text.lower().split()


class BM25Index:
    def __init__(self):
        self.corpus_ids: list[str] = []
        self.corpus_texts: list[str] = []
        self._bm25: BM25Okapi | None = None

    def add_documents(self, ids: list[str], texts: list[str]):
        self.corpus_ids.extend(ids)
        self.corpus_texts.extend(texts)
        tokenized = [tokenize(t) for t in self.corpus_texts]
        self._bm25 = BM25Okapi(tokenized)

    def query(self, query_text: str, top_k: int = 20) -> list[tuple[str, float]]:
        """Returns [(chunk_id, score), ...] sorted by score desc."""
        if not self._bm25 or not self.corpus_ids:
            return []
        tokens = tokenize(query_text)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self.corpus_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(cid, float(score)) for cid, score in ranked[:top_k]]

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"ids": self.corpus_ids, "texts": self.corpus_texts}, f)

    @classmethod
    def load(cls, path: str) -> "BM25Index":
        idx = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        idx.add_documents(data["ids"], data["texts"])
        return idx


# Global index singleton (loaded at startup, rebuilt on reindex)
_global_index: BM25Index | None = None
_global_index_path = os.path.join(settings.BM25_DIR, "global.pkl")


def get_global_index() -> BM25Index:
    global _global_index
    if _global_index is None:
        if os.path.exists(_global_index_path):
            _global_index = BM25Index.load(_global_index_path)
        else:
            _global_index = BM25Index()
    return _global_index


def rebuild_global_index(all_ids: list[str], all_texts: list[str]):
    global _global_index
    _global_index = BM25Index()
    _global_index.add_documents(all_ids, all_texts)
    _global_index.save(_global_index_path)
```

---

### 7.6 ChromaDB Store

`app/vector/chroma.py`

```python
import asyncio
import chromadb
from app.config import settings

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
    # ChromaDB stores metadata as flat dicts — stringify nested values
    metadatas = [_flatten_payload(p) for p in payloads]
    # Also store full text as document for retrieval
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
    # ChromaDB delete accepts list of IDs directly
    await asyncio.to_thread(col.delete, ids=ids)


async def search_dense(
    query_vector: list[float],
    top_k: int = 20,
    filter_source_id: str = None,
) -> list[tuple[str, float, dict]]:
    """
    Dense cosine search. Returns [(chunk_id, score, metadata), ...]
    Note: ChromaDB returns distances (lower = more similar for cosine).
    We convert to similarity scores (1 - distance).
    """
    col = get_collection()
    where = {"source_id": filter_source_id} if filter_source_id else None

    def _query():
        kwargs = {
            "query_embeddings": [query_vector],
            "n_results": min(top_k, col.count() or 1),
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
            score = 1.0 - distance   # convert cosine distance → similarity
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
        # Re-attach text to payload (stored as document in ChromaDB)
        payload = dict(metadata)
        payload["text"] = document
        output.append({"id": chunk_id, "payload": payload})

    return output


def _flatten_payload(payload: dict) -> dict:
    """
    ChromaDB metadata must be flat (str/int/float/bool values only).
    Stringify any nested structures.
    """
    flat = {}
    for k, v in payload.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            flat[k] = v if v is not None else ""
        else:
            flat[k] = str(v)
    return flat
```

---

### 7.7 Ingester Orchestrator

`app/pipeline/ingester.py`

This is the main function that wires everything together.

```python
import asyncio
from datetime import datetime, timezone

from app.config import settings
from app.db.mongo import get_sources_col
from app.pipeline.parser import parse_file, parse_url
from app.pipeline.chunker import build_parent_child_chunks, Chunk
from app.pipeline.enricher import enrich_chunks_batch, generate_summary
from app.pipeline.embedder import embed_texts
from app.vector.chroma import upsert_points, delete_points, ensure_collection
from app.search.bm25 import get_global_index, rebuild_global_index


async def ingest_source(
    *,
    source_doc: dict,        # MongoDB doc (already inserted)
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

    # 3. Delete old vectors if this is a reindex
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
    # Children (enriched) — these are the searchable units
    child_payloads = []
    for chunk, enriched in zip(children, enriched_texts):
        child_payloads.append({
            **chunk.metadata,
            "chunk_id": chunk.id,
            "text": enriched,           # enriched text stored in payload too
            "original_text": chunk.text,
            "chunk_type": "child",
        })

    # Summary
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

    # 9. Parent text stored in MongoDB for fast lookup during context expansion
    # ChromaDB holds child chunks only — parent chunks fetched from Mongo by ID
    parent_map = {p.id: p.text for p in parents}

    # 10. Rebuild global BM25 index (add this source's children)
    _update_global_bm25(
        source_id=source_id,
        child_ids=[c.id for c in children],
        child_texts=enriched_texts,
    )

    # 11. Update MongoDB source doc
    return {
        "status": "indexed",
        "contentHash": content_hash,
        "childChunkIds": [c.id for c in children],
        "parentChunkIds": [p.id for p in parents],
        "summaryChunkId": summary_id,
        "totalChunks": len(children),
        "parentChunkMap": parent_map,   # stored for context expansion
        "lastIndexed": datetime.now(timezone.utc),
    }


def _update_global_bm25(
    source_id: str,
    child_ids: list[str],
    child_texts: list[str],
):
    """Add source chunks to global BM25 (full rebuild needed for accuracy)."""
    # We schedule a full rebuild after all sources are ingested
    # For single-source updates we just flag for rebuild
    pass  # full rebuild called from reindex endpoint after all sources done


async def full_bm25_rebuild():
    """Rebuild global BM25 from all indexed sources in MongoDB."""
    col = get_sources_col()
    sources = await col.find(
        {"status": "indexed", "childChunkIds": {"$exists": True}},
        {"childChunkIds": 1, "parentChunkMap": 1}
    ).to_list(None)

    all_ids = []
    all_texts = []

    # We need the enriched texts — stored in ChromaDB documents
    from app.vector.chroma import get_points_by_ids
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
```

---

## 8. Retrieval Pipeline

### 8.1 Hybrid Search (Dense + BM25 + RRF)

`app/search/hybrid.py`

```python
from app.vector.chroma import search_dense
from app.search.bm25 import get_global_index
from app.config import settings


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

    # Run both in parallel
    dense_results_raw, bm25_results = await asyncio.gather(
        search_dense(query_vector, top_k=top_k_dense),
        asyncio.to_thread(get_global_index().query, query_text, top_k_bm25),
    )
    import asyncio

    # Normalize to [(id, score), ...]
    dense_results = [(r[0], r[1]) for r in dense_results_raw]
    # bm25_results already [(id, score), ...]

    fused = reciprocal_rank_fusion([dense_results, bm25_results])
    return fused[:top_k_fused]


import asyncio
```

---

### 8.2 Reranker

`app/search/reranker.py`

```python
from sentence_transformers import CrossEncoder
import asyncio

# Loaded once at startup — runs on CPU, ~50ms for 30 docs
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
    candidates: list[tuple[str, str]],  # [(chunk_id, chunk_text), ...]
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
```

---

### 8.3 Full Retrieval Chain

`app/retrieval.py`

```python
from app.pipeline.embedder import embed_query
from app.search.hybrid import hybrid_search
from app.search.reranker import rerank
from app.vector.chroma import get_points_by_ids, search_dense
from app.db.mongo import get_sources_col
from app.config import settings


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

    # 4. Rerank → top_k
    reranked = await rerank(query, candidates, top_k=top_k)

    # 5. Parent chunk expansion
    # For each top chunk, get the parent chunk text for richer context
    results = []
    col = get_sources_col()

    for rank, (cid, rerank_score) in enumerate(reranked, start=1):
        point = id_to_point.get(cid)
        if not point:
            continue

        payload = point["payload"]
        source_id = payload.get("source_id")
        parent_id = payload.get("parent_id")

        # Fetch parent text from MongoDB source doc
        parent_text = payload.get("original_text", "")
        if parent_id and source_id:
            source_doc = await col.find_one(
                {"_id": __import__("bson").ObjectId(source_id)},
                {"parentChunkMap": 1}
            )
            if source_doc and source_doc.get("parentChunkMap"):
                parent_text = source_doc["parentChunkMap"].get(parent_id, parent_text)

        results.append({
            "rank": rank,
            "chunk_id": cid,
            "rerank_score": rerank_score,
            "text": parent_text or payload.get("text", ""),  # parent > child
            "source_label": payload.get("source_label", ""),
            "source_url": payload.get("source_url", ""),
            "source_type": payload.get("source_type", ""),
            "source_id": source_id,
            "chunk_type": payload.get("chunk_type", ""),
        })

    return results
```

---

## 9. Admin API — All Endpoints

### 9.1 Auth Middleware

`app/auth.py`

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_scheme = APIKeyHeader(name="x-api-key", auto_error=False)

async def require_api_key(key: str = Security(api_key_scheme)):
    if not key or key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing x-api-key header",
        )
    return key
```

---

### 9.2 POST /admin/upload-file

Upload a file → parse → index. Supported: PDF, DOCX, XLSX, TXT, CSV, HTML.

```bash
curl -X POST https://mcp.time-4-action.com/admin/upload-file \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@company-handbook.pdf" \
  -F "label=Company Handbook 2025"
```

`app/routes/upload_file.py`

```python
import os, uuid, aiofiles
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".csv", ".html", ".md"}

@router.post("/admin/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    label: str = Form(None),
    _: str = Depends(require_api_key),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    dest = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    col = get_sources_col()
    source_doc = {
        "_id": ObjectId(),
        "type": "file",
        "label": label or file.filename,
        "originalName": file.filename,
        "filePath": dest,
        "mimeType": file.content_type,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    await col.insert_one(source_doc)

    updates = await ingest_source(source_doc=source_doc)
    updates["updatedAt"] = datetime.now(timezone.utc)
    await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})

    return {
        "sourceId": str(source_doc["_id"]),
        "label": source_doc["label"],
        "status": updates.get("status"),
        "totalChunks": updates.get("totalChunks", 0),
    }
```

**Response:**
```json
{
  "sourceId": "665f1a2b3c4d5e6f7a8b9c0d",
  "label": "Company Handbook 2025",
  "status": "indexed",
  "totalChunks": 84
}
```

---

### 9.3 POST /admin/add-url

Register and index a single URL.

```bash
curl -X POST https://mcp.time-4-action.com/admin/add-url \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://time-4-action.com/about", "label": "About page"}'
```

`app/routes/add_url.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from datetime import datetime, timezone
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source

router = APIRouter()

class AddUrlBody(BaseModel):
    url: HttpUrl
    label: str | None = None

@router.post("/admin/add-url")
async def add_url(body: AddUrlBody, _: str = Depends(require_api_key)):
    url_str = str(body.url)
    col = get_sources_col()

    # Prevent duplicates
    existing = await col.find_one({"url": url_str})
    if existing:
        raise HTTPException(409, f"URL already registered: {existing['_id']}")

    source_doc = {
        "_id": ObjectId(),
        "type": "url",
        "label": body.label or url_str,
        "url": url_str,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    await col.insert_one(source_doc)

    updates = await ingest_source(source_doc=source_doc)
    updates["updatedAt"] = datetime.now(timezone.utc)
    await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})

    return {
        "sourceId": str(source_doc["_id"]),
        "url": url_str,
        "status": updates.get("status"),
        "totalChunks": updates.get("totalChunks", 0),
    }
```

---

### 9.4 POST /admin/add-urls-bulk

Add multiple URLs at once without needing a sitemap.

```bash
curl -X POST https://mcp.time-4-action.com/admin/add-urls-bulk \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      {"url": "https://time-4-action.com/services", "label": "Services"},
      {"url": "https://time-4-action.com/pricing"},
      {"url": "https://time-4-action.com/faq", "label": "FAQ"}
    ]
  }'
```

`app/routes/add_urls_bulk.py`

```python
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl
from datetime import datetime, timezone
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source
from app.config import settings

router = APIRouter()

class UrlItem(BaseModel):
    url: HttpUrl
    label: str | None = None

class BulkUrlBody(BaseModel):
    urls: list[UrlItem]

@router.post("/admin/add-urls-bulk")
async def add_urls_bulk(body: BulkUrlBody, _: str = Depends(require_api_key)):
    col = get_sources_col()
    results = {"indexed": 0, "skipped": 0, "failed": 0, "sources": []}

    for item in body.urls:
        url_str = str(item.url)
        await asyncio.sleep(settings.CRAWL_DELAY_MS / 1000)
        try:
            existing = await col.find_one({"url": url_str})
            if existing:
                results["skipped"] += 1
                continue

            source_doc = {
                "_id": ObjectId(),
                "type": "url",
                "label": item.label or url_str,
                "url": url_str,
                "status": "pending",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc),
            }
            await col.insert_one(source_doc)
            updates = await ingest_source(source_doc=source_doc)
            updates["updatedAt"] = datetime.now(timezone.utc)
            await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})

            results["indexed"] += 1
            results["sources"].append({
                "sourceId": str(source_doc["_id"]),
                "url": url_str,
                "status": updates.get("status"),
            })
        except Exception as e:
            results["failed"] += 1
            results["sources"].append({"url": url_str, "status": "error", "error": str(e)})

    return results
```

---

### 9.5 POST /admin/upload-sitemap

Upload `sitemap.xml` → extract all URLs → crawl and index everything.

```bash
# From file
curl -X POST https://mcp.time-4-action.com/admin/upload-sitemap \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@sitemap.xml" \
  -F "base_label=time-4-action.com" \
  -F "crawl_now=true"

# From URL (alternative)
curl -X POST https://mcp.time-4-action.com/admin/add-url \
  -H "x-api-key: YOUR_KEY" \
  -d '{"url": "https://time-4-action.com/sitemap.xml", "label": "Sitemap"}'
```

`app/routes/upload_sitemap.py`

```python
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.parser import parse_sitemap_xml
from app.pipeline.ingester import ingest_source, full_bm25_rebuild
from app.config import settings

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
    urls = list(dict.fromkeys(urls))[:settings.MAX_SITEMAP_URLS]  # deduplicate

    col = get_sources_col()

    # Register sitemap root doc
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

    # Rebuild global BM25 after all sources are indexed
    await full_bm25_rebuild()

    return result
```

---

### 9.6 POST /admin/reindex-company-data

Re-crawl and re-index all sources. Hash-based — only reprocesses changed content.
**This is the endpoint at** `https://mcp.time-4-action.com/admin/reindex-company-data`.

```bash
curl -X POST https://mcp.time-4-action.com/admin/reindex-company-data \
  -H "x-api-key: YOUR_KEY"
```

`app/routes/reindex.py`

```python
import time, asyncio
from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source, full_bm25_rebuild
from app.config import settings

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
        await asyncio.sleep(0.1)  # avoid hammering APIs
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

    # Rebuild BM25 once after all updates
    total_bm25_docs = await full_bm25_rebuild()

    stats["durationMs"] = int((time.time() - t0) * 1000)
    stats["bm25DocumentCount"] = total_bm25_docs
    return stats
```

**Response:**
```json
{
  "total": 54,
  "reindexed": 7,
  "unchanged": 45,
  "failed": 2,
  "durationMs": 18400,
  "bm25DocumentCount": 892
}
```

---

### 9.7 GET /admin/sources

List all registered sources with filtering.

```bash
# All sources
curl "https://mcp.time-4-action.com/admin/sources" \
  -H "x-api-key: YOUR_KEY"

# Only URLs with errors
curl "https://mcp.time-4-action.com/admin/sources?type=url&status=error" \
  -H "x-api-key: YOUR_KEY"

# Pagination
curl "https://mcp.time-4-action.com/admin/sources?page=2&limit=25" \
  -H "x-api-key: YOUR_KEY"
```

`app/routes/sources.py` (partial)

```python
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
```

---

### 9.8 GET /admin/source/:id

Get details of a single source.

```bash
curl "https://mcp.time-4-action.com/admin/source/665f1a2b3c4d5e6f7a8b9c0d" \
  -H "x-api-key: YOUR_KEY"
```

---

### 9.9 DELETE /admin/source/:id

Remove source + purge all its vectors from ChromaDB + remove from BM25.

```bash
curl -X DELETE "https://mcp.time-4-action.com/admin/source/665f1a2b3c4d5e6f7a8b9c0d" \
  -H "x-api-key: YOUR_KEY"
```

```python
@router.delete("/admin/source/{source_id}")
async def delete_source(source_id: str, _: str = Depends(require_api_key)):
    col = get_sources_col()
    doc = await col.find_one({"_id": ObjectId(source_id)})
    if not doc:
        raise HTTPException(404, "Source not found")

    # Delete vectors
    all_ids = (
        doc.get("childChunkIds", [])
        + doc.get("parentChunkIds", [])
        + ([doc["summaryChunkId"]] if doc.get("summaryChunkId") else [])
    )
    await delete_points(all_ids)

    # Delete from MongoDB
    await col.delete_one({"_id": doc["_id"]})

    # Rebuild BM25 without this source
    await full_bm25_rebuild()

    return {"deleted": True, "chunksRemoved": len(all_ids)}
```

---

### 9.10 POST /admin/source/:id/reindex

Force reindex a single source (ignores content hash).

```bash
curl -X POST "https://mcp.time-4-action.com/admin/source/665f.../reindex" \
  -H "x-api-key: YOUR_KEY"
```

```python
@router.post("/admin/source/{source_id}/reindex")
async def reindex_single(source_id: str, _: str = Depends(require_api_key)):
    col = get_sources_col()
    doc = await col.find_one({"_id": ObjectId(source_id)})
    if not doc:
        raise HTTPException(404, "Source not found")

    updates = await ingest_source(source_doc=doc, force=True)
    updates["updatedAt"] = datetime.now(timezone.utc)
    await col.update_one({"_id": doc["_id"]}, {"$set": updates})
    await full_bm25_rebuild()

    return {"sourceId": source_id, **updates}
```

---

### 9.11 GET /admin/stats

Overview of the knowledge base state.

```bash
curl "https://mcp.time-4-action.com/admin/stats" \
  -H "x-api-key: YOUR_KEY"
```

**Response:**
```json
{
  "sources": {
    "total": 54,
    "byType": {"file": 8, "url": 12, "sitemap_child": 34},
    "byStatus": {"indexed": 50, "error": 2, "pending": 2}
  },
  "chunks": {
    "totalChildChunks": 892,
    "bm25IndexSize": 892
  },
  "lastReindex": "2025-06-01T14:30:00Z"
}
```

---

### 9.12 POST /admin/search-test

Test the full retrieval pipeline from the admin panel — extremely useful for tuning.

```bash
curl -X POST "https://mcp.time-4-action.com/admin/search-test" \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are our payment terms?", "top_k": 5, "show_scores": true}'
```

`app/routes/search_test.py`

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import require_api_key
from app.retrieval import retrieve

router = APIRouter()

class SearchTestBody(BaseModel):
    query: str
    top_k: int = 5
    show_scores: bool = False

@router.post("/admin/search-test")
async def search_test(body: SearchTestBody, _: str = Depends(require_api_key)):
    results = await retrieve(body.query, top_k=body.top_k)

    output = []
    for r in results:
        item = {
            "rank": r["rank"],
            "source": r["source_label"],
            "url": r.get("source_url", ""),
            "text_preview": r["text"][:300] + "..." if len(r["text"]) > 300 else r["text"],
        }
        if body.show_scores:
            item["rerank_score"] = round(r["rerank_score"], 4)
        output.append(item)

    return {"query": body.query, "results": output}
```

---

## 10. FastAPI App Entry Point

`app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.vector.chroma import ensure_collection
from app.search.reranker import get_reranker
from app.routes import (
    upload_file, add_url, add_urls_bulk,
    upload_sitemap, reindex, sources, search_test
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await ensure_collection()
    get_reranker()           # pre-load reranker model
    print("✅ Knowledge API ready")
    yield
    # Shutdown (nothing needed)

app = FastAPI(
    title="T4A Knowledge API",
    description="RAG pipeline admin + retrieval",
    lifespan=lifespan,
)

app.include_router(upload_file.router)
app.include_router(add_url.router)
app.include_router(add_urls_bulk.router)
app.include_router(upload_sitemap.router)
app.include_router(reindex.router)
app.include_router(sources.router)
app.include_router(search_test.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 11. MCP Tool — company_knowledge

`app/mcp/tool.py`

Add this to your existing FastMCP server at `mcp.time-4-action.com`.

```python
from fastmcp import FastMCP
from app.retrieval import retrieve

mcp = FastMCP("T4A Knowledge")


@mcp.tool()
async def company_knowledge(
    question: str,
    top_k: int = 5,
) -> str:
    """
    Search the T4A company knowledge base.

    Use this tool to answer any questions about:
    - Company products, services, and features
    - Pricing, terms, and policies
    - Internal processes and documentation
    - Technical specifications
    - Contact information and team structure

    Args:
        question: The question or topic to look up
        top_k: Number of relevant passages to return (default 5, max 10)

    Returns:
        Relevant passages from company documents with source attribution.
        Always cite the source when using this information.
    """
    top_k = min(top_k, 10)
    results = await retrieve(question, top_k=top_k)

    if not results:
        return "No relevant information found in the company knowledge base."

    lines = [f"Found {len(results)} relevant passages:\n"]
    for r in results:
        source = r["source_label"]
        if r.get("source_url"):
            source = f"{source} ({r['source_url']})"
        lines.append(f"[{r['rank']}] Source: {source}")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)
```

---

## 12. Docker Setup

`docker-compose.yml`

```yaml
version: "3.9"

services:
  knowledge-api:
    build: .
    restart: unless-stopped
    ports:
      - "8100:8000"
    env_file: .env
    volumes:
      - ./uploads:/app/uploads
      - ./bm25_indexes:/app/bm25_indexes
    depends_on:
      chromadb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  chromadb:
    image: chromadb/chroma:latest
    restart: unless-stopped
    ports:
      - "8001:8000"       # expose on 8001 to avoid conflict with API
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - PERSIST_DIRECTORY=/chroma/chroma
      - ANONYMIZED_TELEMETRY=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  chroma_data:
```



`Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for unstructured (PDF, OCR)
RUN apt-get update && apt-get install -y \
    libmagic1 poppler-utils tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install torch CPU-only first (smaller), then rest
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download reranker model at build time
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY app/ ./app/
RUN mkdir -p /app/uploads /app/bm25_indexes

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## 13. nginx Config

Add to your existing `/etc/nginx/conf.d/mcp.time-4-action.com.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name mcp.time-4-action.com;

    # ... existing SSL config ...

    # Knowledge admin API
    location /admin/ {
        proxy_pass          http://127.0.0.1:8100/admin/;
        proxy_http_version  1.1;
        proxy_set_header    Host $host;
        proxy_set_header    X-Real-IP $remote_addr;
        proxy_read_timeout  300s;       # long timeout for sitemap crawls
        client_max_body_size 100M;      # large PDF uploads
    }

    location /health {
        proxy_pass http://127.0.0.1:8100/health;
    }

    # MCP tool endpoint (existing FastMCP server)
    location /mcp/ {
        proxy_pass http://127.0.0.1:<YOUR_FASTMCP_PORT>/mcp/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 14. First-time ChromaDB Setup

ChromaDB runs as a Docker container alongside the API. On first start it creates an empty collection automatically via `ensure_collection()` at startup.

```bash
# Start everything
docker compose up -d

# Verify ChromaDB is healthy
curl http://localhost:8001/api/v1/heartbeat

# Verify API is up
curl http://localhost:8100/health
```

If you have an **existing ChromaDB collection** from a previous project that you want to preserve, you can point `CHROMA_COLLECTION` in `.env` to that collection name — the pipeline will add to it rather than overwrite.

To start completely fresh:
```bash
# Wipe ChromaDB volume and restart
docker compose down
docker volume rm t4a-knowledge_chroma_data
docker compose up -d
```

---

## 15. Operational Runbook

### First-time setup

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your keys

# 2. Start services
docker compose up -d

# 3. Verify health
curl http://localhost:8100/health

# 4. Upload your first sources
curl -X POST http://localhost:8100/admin/upload-file \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@docs/handbook.pdf"

# 5. Upload site sitemap
curl -X POST http://localhost:8100/admin/upload-sitemap \
  -H "x-api-key: YOUR_KEY" \
  -F "file=@sitemap.xml" \
  -F "base_label=time-4-action.com"

# 6. Test retrieval
curl -X POST http://localhost:8100/admin/search-test \
  -H "x-api-key: YOUR_KEY" \
  -d '{"query": "what services do you offer", "show_scores": true}'
```

### Scheduled reindex (cron)

```bash
# /etc/cron.d/t4a-knowledge
# Reindex every day at 3am
0 3 * * * root curl -s -X POST https://mcp.time-4-action.com/admin/reindex-company-data \
  -H "x-api-key: YOUR_KEY" >> /var/log/t4a-reindex.log 2>&1
```

### Updating a source after content changes

```bash
# Option A: manual force reindex of one source
curl -X POST https://mcp.time-4-action.com/admin/source/SOURCE_ID/reindex \
  -H "x-api-key: YOUR_KEY"

# Option B: full reindex (will skip unchanged sources automatically)
curl -X POST https://mcp.time-4-action.com/admin/reindex-company-data \
  -H "x-api-key: YOUR_KEY"
```

### ChromaDB inspection

ChromaDB doesn't ship with a GUI, but you can inspect your collection via its REST API:

```bash
# Collection info and count
curl http://localhost:8001/api/v1/collections/company_knowledge
curl http://localhost:8001/api/v1/collections/company_knowledge/count
```

In practice, use `/admin/stats` and `/admin/search-test` — these are more useful.

### Monitoring chunk quality

Use `/admin/search-test` regularly with sample questions you expect agents to ask. If you get poor results:

1. **Check `show_scores: true`** — if rerank scores are low (<0), content may not be in the KB
2. **Check `/admin/sources?status=error`** — failed ingestions
3. **Force reindex** a specific source if content changed
4. **Tune chunk sizes** — if answers are cut off, increase `PARENT_CHUNK_SIZE`; if recall is poor, decrease `CHILD_CHUNK_SIZE`
