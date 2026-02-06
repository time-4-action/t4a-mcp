# Building a Production-Grade Knowledge Base System

A step-by-step guide to building a robust RAG system from unstructured data sources.

---

## Phase 1: Data Collection & Ingestion

### 1.1 Identify Your Data Sources
- **Email**: Gmail API, Microsoft Graph API, IMAP
- **Documents**: Google Drive, SharePoint, Dropbox, local file systems
- **Communication**: Slack, Teams, Discord
- **Databases**: PostgreSQL, MongoDB, CRMs
- **Web**: Internal wikis, Confluence, Notion

### 1.2 Build Connectors
For each source, you need:
- Authentication handling (OAuth, API keys)
- Rate limiting and retry logic
- Incremental sync (track last sync timestamp, only fetch new/modified)
- Webhook support where available for real-time updates

### 1.3 Normalize Data Format
Create a unified document schema:
```
{
  "id": "unique-identifier",
  "source": "gmail|slack|drive|...",
  "content": "the actual text",
  "metadata": {
    "author": "...",
    "created_at": "...",
    "updated_at": "...",
    "source_url": "...",
    "thread_id": "...",  // for emails/messages
    "attachments": [...]
  },
  "raw": { ... }  // original data for debugging
}
```

---

## Phase 2: Data Processing Pipeline

### 2.1 Text Extraction
- **PDFs**: PyMuPDF, pdfplumber, or Unstructured.io for complex layouts
- **Office docs**: python-docx, openpyxl, python-pptx
- **Emails**: Parse HTML body, extract plain text, handle attachments separately
- **Images/Scans**: OCR with Tesseract or cloud services (AWS Textract, Google Vision)

### 2.2 Cleaning & Preprocessing
- Remove boilerplate (email signatures, legal disclaimers, reply chains)
- Normalize whitespace and encoding
- Language detection (handle multilingual content)
- Extract and preserve structured data (tables, lists)

### 2.3 Chunking Strategies

**Simple (not recommended for production):**
- Fixed character/token count with overlap

**Better approaches:**

1. **Semantic Chunking**
   - Use sentence embeddings to detect topic shifts
   - Split when similarity between consecutive sentences drops

2. **Document Structure Aware**
   - Respect headers, paragraphs, sections
   - Keep code blocks intact
   - Preserve table structure

3. **Hierarchical/Parent-Child**
   - Create multiple chunk sizes (small for retrieval, large for context)
   - Link child chunks to parent documents
   - Retrieve small, return large

**Chunk size guidelines:**
- 256-512 tokens: Good for precise retrieval
- 1024-2048 tokens: Better context, less precision
- Test with your actual queries to find optimal size

### 2.4 Metadata Enrichment
Add computed metadata:
- Document type classification
- Topic/category detection
- Entity extraction (people, companies, dates, amounts)
- Summary generation (use LLM to create chunk summaries)
- Keywords extraction

---

## Phase 3: Embedding & Indexing

### 3.1 Choose Embedding Model

**Hosted options:**
- OpenAI `text-embedding-3-large` (3072 dims, best quality)
- OpenAI `text-embedding-3-small` (1536 dims, good balance)
- Cohere `embed-v3` (good multilingual support)
- Voyage AI (specialized for code, legal, etc.)

**Self-hosted options:**
- BGE-large-en-v1.5 (open source, very good)
- E5-large-v2
- GTE-large
- Sentence Transformers

**Considerations:**
- Dimension size affects storage and speed
- Some models better for specific domains
- Batch your embedding calls for efficiency

### 3.2 Choose Vector Database

**Managed/Cloud:**
- Pinecone: Easy to use, scales well, expensive
- Weaviate Cloud: Hybrid search built-in
- Qdrant Cloud: Good performance, reasonable pricing

**Self-hosted:**
- Qdrant: Excellent performance, Rust-based
- Milvus: Highly scalable, complex setup
- Weaviate: GraphQL API, hybrid search
- Chroma: Simple, good for prototypes
- pgvector: If you're already on PostgreSQL

**Key features to look for:**
- Metadata filtering
- Hybrid search (vector + keyword)
- Namespaces/collections for multi-tenancy
- Backup and restore
- Horizontal scaling

### 3.3 Indexing Strategy
- Batch insert documents (not one by one)
- Store chunk text + metadata + embedding
- Create indexes on frequently filtered metadata fields
- Consider separate collections for different document types

---

## Phase 4: Retrieval Pipeline

### 4.1 Query Processing
1. **Query understanding**
   - Detect intent (question, search, command)
   - Extract filters from natural language ("emails from last week" → date filter)

2. **Query expansion**
   - Generate synonyms and related terms
   - Use LLM to rephrase query multiple ways
   - HyDE: Generate hypothetical answer, embed that instead

### 4.2 Retrieval Methods

**Basic:** Single vector similarity search

**Better:** Hybrid search
- Combine dense vectors (semantic) with sparse vectors (BM25/keywords)
- Weight between them (typically 0.7 semantic, 0.3 keyword)

**Advanced:** Multi-stage retrieval
1. First stage: Retrieve 50-100 candidates (fast, approximate)
2. Second stage: Rerank to top 5-10 (slow, precise)

### 4.3 Reranking
- Cross-encoders score query-document pairs directly
- Much more accurate than bi-encoders but slower
- Models: Cohere Rerank, BGE-reranker, cross-encoder/ms-marco

### 4.4 Context Assembly
- Deduplicate overlapping chunks
- Order by relevance or chronologically
- Include parent/sibling chunks for more context
- Respect token limits of your LLM

---

## Phase 5: Generation & Response

### 5.1 Prompt Engineering
- Clear system prompt with role and constraints
- Include retrieved context with source attribution
- Ask model to cite sources in response
- Handle "I don't know" gracefully

### 5.2 Citation & Transparency
- Track which chunks contributed to answer
- Return source links/references to user
- Highlight relevant passages
- Show confidence indicators

### 5.3 Answer Quality
- Fact-check against retrieved context
- Detect hallucinations (answer contains info not in context)
- Fallback to "I don't have information about that"

---

## Phase 6: Keeping It Fresh

### 6.1 Incremental Updates
- Track document versions/hashes
- Only re-embed changed documents
- Handle deletions (remove from vector store)
- Timestamp-based sync for each source

### 6.2 Scheduled Jobs
- Full re-sync weekly/monthly (catch missed updates)
- Stale content detection and archival
- Embedding model updates (requires full re-index)

### 6.3 Monitoring
- Track retrieval relevance scores
- Log queries with low-quality results
- Monitor embedding API costs
- Alert on ingestion failures

---

## Phase 7: Evaluation & Iteration

### 7.1 Build Evaluation Dataset
- Collect real user queries
- Create ground truth: query → expected relevant documents
- Include edge cases and failure modes

### 7.2 Metrics to Track
- **Retrieval**: Recall@K, Precision@K, MRR, NDCG
- **Generation**: Answer relevance, faithfulness, completeness
- **System**: Latency (p50, p95), throughput, cost per query

### 7.3 A/B Testing
- Test different chunk sizes
- Compare embedding models
- Experiment with reranking
- Tune hybrid search weights

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  Gmail │ Slack │ Drive │ Confluence │ Databases │ File Systems  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                              │
│  Connectors → Normalization → Deduplication → Queue             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
│  Text Extraction → Cleaning → Chunking → Metadata Enrichment    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INDEXING LAYER                               │
│  Embedding Model → Vector Database → Metadata Index             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL LAYER                               │
│  Query Processing → Hybrid Search → Reranking → Context Assembly│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATION LAYER                              │
│  LLM + Prompt → Response Generation → Citation → Quality Check  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Recommended Stack (Starting Point)

| Component | Recommendation | Why |
|-----------|---------------|-----|
| Orchestration | Python + Celery or Temporal | Reliable job processing |
| Text Extraction | Unstructured.io | Handles many formats |
| Chunking | LangChain + custom logic | Flexible, good defaults |
| Embeddings | OpenAI text-embedding-3-small | Cost-effective, good quality |
| Vector DB | Qdrant (self-hosted) or Pinecone (managed) | Balance of features/cost |
| Reranking | Cohere Rerank API | Easy to integrate, effective |
| LLM | GPT-4o or Claude | Best quality responses |
| Monitoring | LangSmith or custom logging | Track quality over time |

---

## Common Pitfalls to Avoid

1. **Chunking too small or too large** - Test with real queries
2. **Ignoring metadata** - Filtering is often more important than semantic search
3. **No reranking** - Huge quality improvement for small latency cost
4. **Stale data** - Users lose trust if info is outdated
5. **No evaluation** - You can't improve what you don't measure
6. **Over-engineering early** - Start simple, add complexity as needed
7. **Ignoring edge cases** - Empty results, irrelevant results, conflicting info

---

## Next Steps

1. Start with a single data source (e.g., a folder of documents)
2. Build basic pipeline: load → chunk → embed → retrieve
3. Test with real queries, identify gaps
4. Add complexity incrementally (hybrid search, reranking, more sources)
5. Build evaluation dataset from real usage
6. Iterate based on metrics
