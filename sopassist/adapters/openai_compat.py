"""Adapter for any OpenAI-compatible API (Gemini's OpenAI endpoint, OpenAI, Groq, Ollama...).

Retry policy: generation and embedding calls are read-only/idempotent, so we retry on
timeouts, 429 and 5xx with exponential backoff + jitter. 4xx (bad key, bad request) never retried."""
from __future__ import annotations

import logging
import random
import time

import httpx

from ..errors import UpstreamError, UpstreamTimeout
from ..ports import LLMResult

log = logging.getLogger("sopassist.llm")


class _Http:
    def __init__(self, base_url: str, api_key: str, timeout_s: float, max_retries: int):
        self.base = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.timeout = timeout_s
        self.max_retries = max_retries

    def post(self, path: str, payload: dict) -> dict:
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = httpx.post(f"{self.base}{path}", json=payload, headers=self.headers, timeout=self.timeout)
                if r.status_code == 429 or r.status_code >= 500:
                    last = UpstreamError(f"upstream status {r.status_code}")
                elif r.status_code >= 400:
                    raise UpstreamError(f"upstream rejected request ({r.status_code})")  # not retried
                else:
                    return r.json()
            except httpx.TimeoutException:
                last = UpstreamTimeout("upstream timed out")
            except httpx.TransportError:
                last = UpstreamError("upstream connection error")
            if attempt < self.max_retries:
                time.sleep(min(8, 0.5 * 2 ** attempt) + random.random() * 0.25)
        raise last or UpstreamError("upstream failed")


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 20, max_retries: int = 2):
        self.model_id = model
        self._http = _Http(base_url, api_key, timeout_s, max_retries)

    def generate(self, system: str, user: str) -> LLMResult:
        t0 = time.perf_counter()
        data = self._http.post("/chat/completions", {
            "model": self.model_id, "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        usage = data.get("usage") or {}
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise UpstreamError("malformed upstream response")
        return LLMResult(text.strip(), self.model_id, int(usage.get("prompt_tokens", 0)),
                         int(usage.get("completion_tokens", 0)), (time.perf_counter() - t0) * 1000)


class OpenAICompatEmbedder:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 20, max_retries: int = 2):
        self.embedder_id = model
        self._http = _Http(base_url, api_key, timeout_s, max_retries)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 50):
            data = self._http.post("/embeddings", {"model": self.embedder_id, "input": texts[i:i + 50]})
            try:
                out.extend(d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"]))
            except (KeyError, TypeError):
                raise UpstreamError("malformed embedding response")
        return out
