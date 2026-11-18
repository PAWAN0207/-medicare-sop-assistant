"""Interfaces owned by us. Domain/RAG code depends only on these, never on a vendor SDK."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: float


class LLMClient(Protocol):
    model_id: str

    def generate(self, system: str, user: str) -> LLMResult: ...


class Embedder(Protocol):
    embedder_id: str   # changing this invalidates stored vectors (index refuses to mix)

    def embed(self, texts: list[str]) -> list[list[float]]: ...
