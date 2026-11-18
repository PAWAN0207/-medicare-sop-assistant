"""Tokenisation shared by the fake embedder, BM25 and the relevance gate."""
from __future__ import annotations

import re

STOPWORDS = frozenset("""a an and are as at be by can do does for from how i if in into is it its me my of on or our
should that the their them then there these they this to up us was we what when where which who whom why will with would you
your much many long often any show shows tell give get make take need needs happens happen""".split())

# tiny, domain-neutral abbreviation map (extend per client glossary)
SYNONYMS = {"fridge": "refrigerator", "meds": "medicine", "med": "medicine", "doc": "doctor", "percentage": "percent", "kept": "keep", "hrs": "hour", "hr": "hour"}

_TOKEN = re.compile(r"[a-z0-9]+")


def stem(tok: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)]
    return tok


def tokens(text: str, drop_stop: bool = True) -> list[str]:
    out = []
    for t in _TOKEN.findall(text.lower().replace("%", " percent ")):
        if drop_stop and t in STOPWORDS:
            continue
        out.append(stem(SYNONYMS.get(t, t)))
    return out


def normalize_question(q: str) -> str:
    return " ".join(q.lower().split()).strip(" ?.!")
