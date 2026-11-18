"""Deterministic, offline stand-ins used by tests and PROVIDER=fake."""
from __future__ import annotations

import hashlib
import math
import re

from ..domain.text import tokens
from ..ports import LLMResult

DIM = 1024


class HashEmbedder:
    """Hashed bag of unigrams+bigrams. Lexical, not semantic."""
    embedder_id = "fake-hash-1024"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        toks = tokens(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        v = [0.0] * DIM

        for feature in feats:
            h = int(hashlib.md5(feature.encode()).hexdigest()[:8], 16)
            v[h % DIM] += 1.0

        v = [1 + math.log(x) if x > 0 else 0.0 for x in v]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0

        return [x / norm for x in v]


# Parse each citation block independently.
_BLOCK = re.compile(
    r"^\[(C\d+)\]\s+([^\r\n]+)\r?\n(.*?)(?=^\[C\d+\]\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)


class FakeLLM:
    """
    Deterministic offline LLM substitute.

    Echoes retrieved excerpts with their original citation markers.
    Used for testing retrieval, access control, citations and caching.
    It does not evaluate real language-generation quality.
    """

    model_id = "fake-extractive"

    def __init__(self, max_excerpts: int = 6):
        self.max_excerpts = max_excerpts
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def _normalise_text(text: str) -> str:
        """Collapse PDF line breaks and repeated whitespace."""
        return re.sub(r"\s+", " ", text).strip()

    def generate(self, system: str, user: str) -> LLMResult:
        self.calls.append((system, user))

        if "EXCERPTS:" not in user:
            text = "NOT_COVERED"
        else:
            excerpt_text = user.split("EXCERPTS:", 1)[1]
            blocks = _BLOCK.findall(excerpt_text)

            if not blocks:
                text = "NOT_COVERED"
            else:
                picked = blocks[:self.max_excerpts]
                lines = []

                for citation_id, heading, body in picked:
                    clean_heading = self._normalise_text(heading)
                    clean_body = self._normalise_text(body)

                    if not clean_body:
                        continue

                    lines.append(
                        f"- {clean_heading}\n"
                        f"  {clean_body} [{citation_id}]"
                    )

                if lines:
                    text = "Based on the current SOPs:\n" + "\n".join(lines)
                else:
                    text = "NOT_COVERED"

        # Keep the original LLMResult positional interface.
        return LLMResult(
            text,
            self.model_id,
            len(user) // 4,
            len(text) // 4,
            0.1,
        )