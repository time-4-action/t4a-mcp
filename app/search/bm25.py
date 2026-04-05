import os
import pickle
from rank_bm25 import BM25Okapi
import app.config as settings


def tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
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
    if all_ids:
        _global_index.add_documents(all_ids, all_texts)
        _global_index.save(_global_index_path)
