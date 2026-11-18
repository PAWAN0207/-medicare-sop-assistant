"""The question-answering use case. Order of operations is the security design:
  user lookup -> PII guard -> cache lookup -> access-filtered retrieval -> relevance gate -> LLM -> citation check
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict

from ..config import Settings
from ..domain.access import AccessPolicy, UserDirectory
from ..domain.models import Answer, Citation
from ..domain.pii import detect_patient_data
from ..domain.text import normalize_question
from ..errors import IndexEmpty, InvalidRequest, PatientDataDetected
from ..ports import Embedder, LLMClient
from ..store.sqlite_store import SqliteStore
from .prompts import NOT_COVERED, PROMPT_VERSION, SYSTEM, build_user_prompt
from .retriever import Retriever

log = logging.getLogger("sopassist.qa")
_MARK = re.compile(r"\[C(\d+)\]")
REFUSAL_TEXT = ("I don't know - the current SOPs available to your role don't cover this. "
                "Please check with your Clinic Manager or HR rather than relying on a guess.")
MAX_Q_CHARS = 1000


def cache_key(question: str, levels: frozenset[str], generation: int, llm_id: str, embedder_id: str,
              search_mode: str) -> str:
    """Everything that can change the answer is in the key:
    question, the *set of access levels* (not the user - same levels => same visible docs => same answer),
    index generation (bumped on every content change), prompt version, model, embedder, search mode."""
    raw = json.dumps([normalize_question(question), sorted(levels), generation, PROMPT_VERSION,
                      llm_id, embedder_id, search_mode], separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class QAService:
    def __init__(self, settings: Settings, store: SqliteStore, llm: LLMClient, embedder: Embedder,
                 policy: AccessPolicy, users: UserDirectory):
        self.s, self.store, self.llm, self.embedder = settings, store, llm, embedder
        self.policy, self.users = policy, users
        self.retriever = Retriever(store, embedder, settings.top_k, settings.search_mode)

    def ask(self, user_id: str, question: str) -> tuple[Answer, bool]:
        """Returns (answer, served_from_cache)."""
        question = (question or "").strip()
        if not question or len(question) > MAX_Q_CHARS:
            raise InvalidRequest(f"question must be 1-{MAX_Q_CHARS} characters")
        user = self.users.get(user_id)                       # raises UnknownUser
        pii = detect_patient_data(question)
        if pii:                                              # nothing below ever sees this text
            log.info("blocked: patient data in question", extra={"pii_types": pii, "role": user.role})
            raise PatientDataDetected("Please remove patient identifiers and ask again.", types=pii)
        levels = self.policy.levels_for_role(user.role)

        key = cache_key(question, levels, self.store.generation(), self.llm.model_id,
                        self.embedder.embedder_id, self.s.search_mode)
        hit = self.store.cache_get(key)
        if hit:
            log.info("cache hit", extra={"role": user.role})
            return _from_payload(hit), True

        r = self.retriever.retrieve(question, levels)
        if self.store.documents() == {}:
            raise IndexEmpty("The SOP index is empty; run ingestion first.")
        if not r.chunks or (r.coverage < self.s.min_term_coverage and r.best_cosine < self.s.min_cosine):
            ans = Answer(REFUSAL_TEXT, True, [], r.generation, "no_relevant_sop")
        else:
            res = self.llm.generate(SYSTEM, build_user_prompt(question, r.chunks))
            cost = (res.tokens_in * self.s.price_in_per_1m + res.tokens_out * self.s.price_out_per_1m) / 1e6
            log.info("llm call", extra={"model": res.model, "latency_ms": round(res.latency_ms, 1),
                                        "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
                                        "cost_usd": round(cost, 6)})
            ans = self._to_answer(res.text, r)

        # key uses the generation that retrieval actually read, so a re-index racing with this request
        # can only produce an entry nobody will ever look up again.
        key2 = cache_key(question, levels, r.generation, self.llm.model_id, self.embedder.embedder_id,
                         self.s.search_mode)
        self.store.cache_put(key2, r.generation, _to_payload(ans), self.s.cache_ttl_s)
        return ans, False

    @staticmethod
    def _to_answer(text: str, r) -> Answer:
        text = text.strip()
        if text.startswith(NOT_COVERED):
            return Answer(REFUSAL_TEXT, True, [], r.generation, "llm_not_covered")
        used = sorted({int(m) for m in _MARK.findall(text) if 1 <= int(m) <= len(r.chunks)})
        if not used:   # an answer with no valid citation is treated as ungrounded -> refuse
            return Answer(REFUSAL_TEXT, True, [], r.generation, "ungrounded")
        seen, cites = set(), []
        for i in used:
            c = r.chunks[i - 1]
            k = (c.sop_id, c.version, c.section_no, c.page)
            if k not in seen:
                seen.add(k)
                cites.append(Citation(c.sop_id, c.version, c.title, c.section_no, c.section_title, c.page))
        return Answer(text, False, cites, r.generation)


def _to_payload(a: Answer) -> dict:
    return asdict(a)


def _from_payload(p: dict) -> Answer:
    return Answer(p["answer"], p["refused"], [Citation(**c) for c in p["citations"]],
                  p["index_generation"], p.get("reason", ""))
