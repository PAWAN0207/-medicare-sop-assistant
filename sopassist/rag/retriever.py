"""Hybrid retrieval (BM25 + vector, fused with RRF) over ONLY the chunks the caller may read,
plus a deterministic relevance gate that decides 'we have nothing on this' before any LLM call."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

from ..domain.models import StoredChunk
from ..domain.text import tokens
from ..ports import Embedder
from ..store.sqlite_store import SqliteStore


@dataclass
class Retrieval:
    generation: int
    chunks: list[StoredChunk]       # top-k, best first
    coverage: float                 # idf-weighted share of query terms found in the best-covering chunk
    best_cosine: float


def _bm25(query_toks: list[str], docs: list[list[str]], k1=1.5, b=0.75) -> np.ndarray:
    n = len(docs)
    avg = sum(len(d) for d in docs) / max(n, 1)
    df = Counter(t for d in docs for t in set(d))
    scores = np.zeros(n)
    for i, d in enumerate(docs):
        tf = Counter(d)
        for t in set(query_toks):
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                scores[i] += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avg))
    return scores


def _rank(scores: np.ndarray) -> dict[int, int]:
    order = np.argsort(-scores, kind="stable")
    return {int(i): r for r, i in enumerate(order)}


class Retriever:
    def __init__(self, store: SqliteStore, embedder: Embedder, top_k: int = 5, mode: str = "hybrid"):
        self.store, self.embedder, self.top_k, self.mode = store, embedder, top_k, mode

    def retrieve(self, question: str, levels: frozenset[str]) -> Retrieval:
        gen, chunks, mat = self.store.read_allowed_chunks(levels)   # access filter happens in SQL
        if not chunks:
            return Retrieval(gen, [], 0.0, 0.0)
        qv = np.asarray(self.embedder.embed([question])[0], dtype=np.float32)
        cos = mat @ qv / (np.linalg.norm(mat, axis=1) * (np.linalg.norm(qv) or 1.0) + 1e-9)
        q_toks = tokens(question)
        doc_toks = [tokens(f"{c.sop_id} {c.title} {c.section_title} {c.text}") for c in chunks]
        bm = _bm25(q_toks, doc_toks)
        if self.mode == "vector":
            fused = cos.copy()
        else:
            rv, rb = _rank(cos), _rank(bm)
            fused = np.array([1 / (60 + rv[i]) + (1 / (60 + rb[i]) if bm[i] > 0 else 0) for i in range(len(chunks))])
        top = [int(i) for i in np.argsort(-fused, kind="stable")[: self.top_k]]
        return Retrieval(gen, [chunks[i] for i in top], _coverage(q_toks, doc_toks), float(cos[top[0]]))


def _coverage(q_toks: list[str], doc_toks: list[list[str]]) -> float:
    """How much of the question's *informative* vocabulary appears in a single chunk.
    Weighted by idf so words present in every chunk ('medicare', 'clinic') count for little and words
    absent from the whole library ('amoxicillin', 'CEO') weigh a lot."""
    q = set(q_toks)
    if not q:
        return 0.0
    n = len(doc_toks)
    df = Counter(t for d in doc_toks for t in set(d))
    idf = {t: math.log(1 + (n + 1) / (df.get(t, 0) + 0.5)) for t in q}
    total = sum(idf.values())
    return max(sum(idf[t] for t in q if t in set(d)) / total for d in doc_toks)
