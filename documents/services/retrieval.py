"""Hybrid retrieval: BM25 (keywords) + char n-gram TF-IDF (fuzzy / Persian morphology),
merged with Reciprocal Rank Fusion. Wrapped as a LangChain retriever.

No embedding model download is needed, so it works offline and with Persian text.
"""
import re
import threading
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

_TRANS = str.maketrans(
    {
        "ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "أ": "ا", "إ": "ا",
        "‌": " ",
        **{c: str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")},
        **{c: str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")},
    }
)
_HARAKAT = re.compile("[ً-ٰٟ]")
_TOKEN = re.compile(r"\w+", re.UNICODE)
RRF_K = 60


def normalize(text: str) -> str:
    return _HARAKAT.sub("", text.translate(_TRANS)).lower()


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


class HybridIndex:
    def __init__(self, chunks):
        """chunks: list of models.Chunk (with .document loaded)."""
        self.chunks = list(chunks)
        texts = [normalize(c.text) for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks]) if texts else None
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(texts) if texts else None

    def search(self, query: str, k: int = 4) -> list[LCDocument]:
        if not self.chunks or not query.strip():
            return []
        n = len(self.chunks)
        pool = min(n, max(k * 4, 10))

        bm25_scores = self.bm25.get_scores(tokenize(query))
        tfidf_scores = linear_kernel(self.vectorizer.transform([normalize(query)]), self.matrix).ravel()

        fused: dict[int, float] = {}
        for scores in (bm25_scores, tfidf_scores):
            order = sorted(range(n), key=lambda i: scores[i], reverse=True)[:pool]
            for rank, i in enumerate(order):
                if scores[i] > 0:
                    fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)

        results = []
        for i, score in sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]:
            c = self.chunks[i]
            results.append(
                LCDocument(
                    page_content=c.text,
                    metadata={
                        "document_id": c.document_id,
                        "title": c.document.title,
                        "chunk_index": c.index,
                        "score": round(score, 5),
                    },
                )
            )
        return results


class HybridRetriever(BaseRetriever):
    index: Any
    k: int = 4

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[LCDocument]:
        return self.index.search(query, self.k)


# ---- cached index, rebuilt automatically when chunks change ----
_lock = threading.Lock()
_cache: dict[str, Any] = {"version": None, "index": None}


def _db_version():
    from django.db.models import Count, Max

    from documents.models import Chunk

    agg = Chunk.objects.aggregate(n=Count("id"), m=Max("id"))
    return (agg["n"], agg["m"])


def get_index() -> HybridIndex:
    from documents.models import Chunk

    version = _db_version()
    with _lock:
        if _cache["version"] != version:
            chunks = Chunk.objects.select_related("document")
            _cache["index"] = HybridIndex(chunks)
            _cache["version"] = version
        return _cache["index"]


def get_retriever(k: int) -> HybridRetriever:
    return HybridRetriever(index=get_index(), k=k)
