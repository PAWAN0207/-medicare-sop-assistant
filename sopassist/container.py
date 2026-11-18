"""Composition root: the only place that knows which concrete adapters are used."""
from __future__ import annotations

from .adapters.fake import FakeLLM, HashEmbedder
from .adapters.openai_compat import OpenAICompatEmbedder, OpenAICompatLLM
from .config import Settings
from .domain.access import AccessPolicy, UserDirectory
from .errors import AppError
from .rag.service import QAService
from .store.sqlite_store import SqliteStore


def build_providers(s: Settings):
    if s.provider == "fake":
        return FakeLLM(), HashEmbedder()
    if s.provider == "openai_compat":
        if not s.llm_api_key:
            raise AppError("LLM_API_KEY is required when PROVIDER=openai_compat")
        return (OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_model, s.llm_timeout_s, s.llm_max_retries),
                OpenAICompatEmbedder(s.llm_base_url, s.llm_api_key, s.embed_model, s.llm_timeout_s, s.llm_max_retries))
    raise AppError(f"Unknown PROVIDER {s.provider!r}")


def build_service(s: Settings, store: SqliteStore | None = None, llm=None, embedder=None) -> QAService:
    if llm is None or embedder is None:
        llm, embedder = build_providers(s)
    store = store or SqliteStore(s.db_path)
    return QAService(s, store, llm, embedder, AccessPolicy.load(s.policy_path), UserDirectory.from_csv(s.users_path))
