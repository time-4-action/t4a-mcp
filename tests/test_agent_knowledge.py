"""/agent/knowledge/* with retrieve() and MongoDB mocked: no network, no models."""

import asyncio
from datetime import datetime

import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.config as settings
from app.auth import require_api_key
from app.routes import agent_knowledge

AGENT_KEY = "agent-key"
ADMIN_KEY = "admin-key"
LONG_TEXT = "x" * 5000


@pytest.fixture
def calls(monkeypatch):
    seen = []

    async def fake_retrieve(query, top_k):
        seen.append((query, top_k))
        return [
            {
                "rank": 1,
                "chunk_id": "c1",
                "rerank_score": 7.5,
                "text": LONG_TEXT,
                "source_label": "Warranty terms",
                "source_url": "",
                "source_type": "file",
                "source_id": "s1",
                "chunk_type": "child",
            },
            {
                "rank": 2,
                "chunk_id": "c2",
                "rerank_score": 1.25,
                "text": "Short page text",
                "source_label": "Shipping",
                "source_url": "https://example.com/shipping",
                "source_type": "url",
                "source_id": "s2",
                "chunk_type": "child",
            },
        ]

    monkeypatch.setattr(agent_knowledge, "_retrieve", fake_retrieve)
    monkeypatch.setattr(settings, "AGENT_READ_KEY", AGENT_KEY)
    monkeypatch.setattr(settings, "ADMIN_API_KEY", ADMIN_KEY)
    return seen


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction):
        self.docs = sorted(self.docs, key=lambda d: d[key], reverse=direction == -1)
        return self

    async def to_list(self, length):
        return self.docs


class FakeCol:
    def __init__(self, docs):
        self.docs = docs
        self.projection = None

    def find(self, query, projection=None):
        self.projection = projection
        return FakeCursor(list(self.docs))


@pytest.fixture
def client():
    api = FastAPI()
    api.include_router(agent_knowledge.router)
    return TestClient(api)


def search(client, key=AGENT_KEY, **body):
    headers = {"x-api-key": key} if key is not None else {}
    return client.post("/agent/knowledge/search", json={"query": "warranty", **body}, headers=headers)


def test_missing_key_is_401(client, calls):
    assert search(client, key=None).status_code == 401
    assert client.get("/agent/knowledge/sources").status_code == 401
    assert calls == []


def test_wrong_key_is_401(client, calls):
    assert search(client, key="nope").status_code == 401
    assert client.get("/agent/knowledge/sources", headers={"x-api-key": "nope"}).status_code == 401


def test_admin_key_does_not_open_agent_routes(client, calls):
    assert search(client, key=ADMIN_KEY).status_code == 401
    assert client.get("/agent/knowledge/sources", headers={"x-api-key": ADMIN_KEY}).status_code == 401


def test_agent_key_does_not_open_admin_routes(calls):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_api_key(AGENT_KEY))
    assert exc.value.status_code == 401


def test_unset_key_is_503(client, calls, monkeypatch):
    monkeypatch.setattr(settings, "AGENT_READ_KEY", "")
    assert search(client, key="").status_code == 503
    assert search(client, key="anything").status_code == 503


def test_search_shape_and_no_truncation_below_cap(client, calls):
    r = search(client, top_k=2)
    assert r.status_code == 200
    assert calls == [("warranty", 2)]
    first, second = r.json()["results"]
    assert set(first) == {"source_id", "source_title", "source_type", "source_url", "text", "score"}
    assert first == {
        "source_id": "s1",
        "source_title": "Warranty terms",
        "source_type": "file",
        "source_url": None,
        "text": "x" * agent_knowledge.MAX_TEXT_CHARS,
        "score": 7.5,
    }
    assert second["source_url"] == "https://example.com/shipping"
    assert second["text"] == "Short page text"


def test_search_text_longer_than_admin_preview(client, calls):
    # /admin/search-test cuts at 300 chars; the agent route keeps up to 4000.
    text = search(client).json()["results"][0]["text"]
    assert len(text) == 4000


def test_top_k_default_and_bounds(client, calls):
    assert search(client).status_code == 200
    assert calls[-1] == ("warranty", 5)
    assert search(client, top_k=10).status_code == 200
    assert search(client, top_k=1).status_code == 200
    assert search(client, top_k=0).status_code == 422
    assert search(client, top_k=11).status_code == 422


def test_query_bounds(client, calls):
    assert search(client, query="").status_code == 422
    assert search(client, query="q" * 501).status_code == 422
    assert search(client, query="q" * 500).status_code == 200


def test_sources_shape(client, calls, monkeypatch):
    oid_old, oid_new = ObjectId(), ObjectId()
    col = FakeCol([
        {
            "_id": oid_old,
            "type": "file",
            "label": "Warranty terms",
            "originalName": "warranty.pdf",
            "filePath": "/app/uploads/abc.pdf",
            "totalChunks": 12,
            "createdAt": datetime(2026, 10, 1),
        },
        {
            "_id": oid_new,
            "type": "url",
            "label": "Shipping",
            "url": "https://example.com/shipping",
            "totalChunks": 3,
            "createdAt": datetime(2026, 11, 1),  # motor default: naive UTC
        },
    ])
    monkeypatch.setattr(agent_knowledge, "get_sources_col", lambda: col)

    r = client.get("/agent/knowledge/sources", headers={"x-api-key": AGENT_KEY})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    newest, oldest = body["items"]
    assert newest == {
        "source_id": str(oid_new),
        "title": "Shipping",
        "type": "url",
        "url": "https://example.com/shipping",
        "chunks": 3,
        "created_at": "2026-11-01T00:00:00Z",
    }
    assert oldest["url"] is None and oldest["title"] == "Warranty terms"
    assert "filePath" not in str(body) and "/app/uploads" not in str(body)
    assert "filePath" not in col.projection
