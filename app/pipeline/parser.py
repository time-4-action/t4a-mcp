import hashlib
import xml.etree.ElementTree as ET

import httpx
import trafilatura
from unstructured.partition.auto import partition


async def parse_file(file_path: str) -> tuple[str, str]:
    """Parse a file using unstructured. Returns (text, content_hash)."""
    elements = partition(filename=file_path)
    text = "\n\n".join(str(e) for e in elements if str(e).strip())
    return text, _hash(text)


async def parse_url(url: str) -> tuple[str, str]:
    """Fetch URL and extract clean text. Returns (text, content_hash)."""
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
    NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.fromstring(content)
    urls = []
    for loc in root.findall(f"{{{NS}}}sitemap/{{{NS}}}loc"):
        urls.append(loc.text.strip())
    for loc in root.findall(f"{{{NS}}}url/{{{NS}}}loc"):
        urls.append(loc.text.strip())
    return urls


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
