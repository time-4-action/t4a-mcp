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
