import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "t4a")

# ChromaDB HTTP service
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "company_knowledge")

# OpenAI (embeddings)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Anthropic (Claude enrichment)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ENRICH_MODEL = os.getenv("ENRICH_MODEL", "claude-haiku-4-5-20251001")

# Admin auth (reuse existing API_KEY env var)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", os.getenv("API_KEY", ""))

# Storage
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
BM25_DIR = os.getenv("BM25_DIR", "/app/bm25_indexes")

# Crawling
CRAWL_DELAY_MS = int(os.getenv("CRAWL_DELAY_MS", "500"))
MAX_SITEMAP_URLS = int(os.getenv("MAX_SITEMAP_URLS", "500"))

# Pipeline tuning
PARENT_CHUNK_SIZE = int(os.getenv("PARENT_CHUNK_SIZE", "800"))
PARENT_CHUNK_OVERLAP = int(os.getenv("PARENT_CHUNK_OVERLAP", "100"))
CHILD_CHUNK_SIZE = int(os.getenv("CHILD_CHUNK_SIZE", "200"))
CHILD_CHUNK_OVERLAP = int(os.getenv("CHILD_CHUNK_OVERLAP", "20"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "100"))
TOP_K_DENSE = int(os.getenv("TOP_K_DENSE", "20"))
TOP_K_BM25 = int(os.getenv("TOP_K_BM25", "20"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))
