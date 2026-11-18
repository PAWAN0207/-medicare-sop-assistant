"""All configuration comes from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("PROVIDER", "fake"))  # fake | openai_compat
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "var/sop_index.db"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    # LLM provider (OpenAI-compatible: Gemini, OpenAI, Groq, Ollama ...)
    llm_base_url: str = field(default_factory=lambda: os.getenv(
        "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gemini-2.0-flash"))
    embed_model: str = field(default_factory=lambda: os.getenv("EMBED_MODEL", "gemini-embedding-001"))
    llm_timeout_s: float = field(default_factory=lambda: _f("LLM_TIMEOUT_S", 20))
    llm_max_retries: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", 2)))
    price_in_per_1m: float = field(default_factory=lambda: _f("PRICE_IN_PER_1M_USD", 0.10))
    price_out_per_1m: float = field(default_factory=lambda: _f("PRICE_OUT_PER_1M_USD", 0.40))
    # Retrieval
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", 6)))
    search_mode: str = field(default_factory=lambda: os.getenv("SEARCH_MODE", "hybrid"))  # vector | hybrid
    min_term_coverage: float = field(default_factory=lambda: _f("MIN_TERM_COVERAGE", 0.55))
    min_cosine: float = field(default_factory=lambda: _f("MIN_COSINE", 0.99))
    # Cache / ingest safety
    cache_ttl_s: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_S", 86400)))
    max_removal_fraction: float = field(default_factory=lambda: _f("MAX_REMOVAL_FRACTION", 0.5))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    @property
    def policy_path(self) -> Path:
        return self.data_dir / "access_policy.json"

    @property
    def users_path(self) -> Path:
        return self.data_dir / "staff_users.csv"
