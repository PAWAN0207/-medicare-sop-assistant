"""Deterministic, offline stand-ins used by tests and `PROVIDER=fake`."""
from __future__ import annotations

import hashlib
import math
import re

from ..domain.text import tokens
from ..ports import LLMResult

DIM = 1024


class HashEmbedder:
    """Hashed bag of unigrams+bigrams. Lexical, not semantic - good enough to exercise the pipeline."""
    embedder_id = "fake-hash-1024"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        toks = tokens(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        v = [0.0] * DIM
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest()[:8], 16)
            v[h % DIM] += 1.0
        v = [1 + math.log(x) if x > 0 else 0.0 for x in v]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


_BLOCK = re.compile(r"\[(C\d+)\] (.*?)\n(.*?)(?=\n\[C\d+\] |\Z)", re.S)


class FakeLLM:
    """Echo 'LLM': quotes every retrieved excerpt with its [C#] marker (so offline eval measures retrieval,
    access control, citations and caching - NOT answer quality, which needs a real model).
    Deterministic, free, and lets us test citation plumbing, access control and caching."""
    model_id = "fake-extractive"

    def __init__(self, max_excerpts: int = 6):
        self.max_excerpts = max_excerpts
        self.calls: list[tuple[str, str]] = []   # tests inspect exactly what the LLM was shown

    def generate(self, system: str, user: str) -> LLMResult:
        self.calls.append((system, user))
        question = user.split("QUESTION:", 1)[-1].split("EXCERPTS:", 1)[0]
        blocks = _BLOCK.findall(user.split("EXCERPTS:", 1)[-1])
        if not blocks:
            text = "NOT_COVERED"
        else:
            picked = blocks[: self.max_excerpts]
            lines = [f"- {head.strip()}: {' '.join(body.split())} [{cid}]" for cid, head, body in picked]
            text = "Based on the current SOPs:\n" + "\n".join(lines)
        return LLMResult(text, self.model_id, len(user) // 4, len(text) // 4, 0.1)
