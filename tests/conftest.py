import os

os.environ.setdefault("SOPASSIST_NO_DOTENV", "1")   # tests must not depend on a developer's local .env

from pathlib import Path

import pytest

import sopassist.ingest.indexer as _indexer_module

from sopassist.adapters.fake import FakeLLM, HashEmbedder
from sopassist.config import Settings
from sopassist.domain.access import AccessPolicy, UserDirectory
from sopassist.ingest.indexer import Indexer
from sopassist.rag.service import QAService
from sopassist.store.sqlite_store import SqliteStore

DATA = Path(__file__).resolve().parent.parent / "data"
ORIGINAL = DATA / "sops"
UPDATE = DATA / "sop_updates" / "2026-11-01"


class CountingEmbedder(HashEmbedder):
    def __init__(self):
        self.texts_embedded = 0

    def embed(self, texts):
        self.texts_embedded += len(texts)
        return super().embed(texts)


@pytest.fixture(scope="session")
def policy():
    return AccessPolicy.load(DATA / "access_policy.json")


@pytest.fixture(scope="session")
def users():
    return UserDirectory.from_csv(DATA / "staff_users.csv")


@pytest.fixture
def settings():
    return Settings(provider="fake", db_path=":memory:", data_dir=DATA)


@pytest.fixture
def embedder():
    return CountingEmbedder()


@pytest.fixture
def store():
    return SqliteStore(":memory:")


@pytest.fixture
def indexer(store, embedder, policy):
    return Indexer(store, embedder, policy)


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def service(settings, store, llm, embedder, policy, users, indexer):
    indexer.run(ORIGINAL)
    return QAService(settings, store, llm, embedder, policy, users)


# PDF parsing is deterministic and slow-ish: memoise it for the test session (indexer logic is still fully exercised).
_real_parse = _indexer_module.parse_pdf


_parse_cache: dict[str, object] = {}


def _cached_parse(path, policy):
    key = str(path)
    if key not in _parse_cache:     # the policy is the same for the whole session
        _parse_cache[key] = _real_parse(path, policy)
    return _parse_cache[key]


@pytest.fixture(autouse=True, scope="session")
def _fast_parse():
    _indexer_module.parse_pdf = _cached_parse
    yield
    _indexer_module.parse_pdf = _real_parse
