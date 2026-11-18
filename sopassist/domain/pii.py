"""Patient-data guard. Deterministic regex rules (no LLM). Returns only the *types* found,
never the matched values, so nothing sensitive gets logged or echoed back.

Known limitation: free-text names are caught only with a title/'patient' cue. A production
system should add an NER/DLP service (e.g. Google Cloud DLP / Presidio) behind the same function."""
from __future__ import annotations

import re

_NAME_STOP = {
    "registration", "data", "complaints", "complaint", "identity", "privacy", "records", "record",
    "safety", "care", "experience", "information", "name", "id", "without", "with", "who", "is",
    "has", "needs", "asks", "wants", "refuses", "arrives", "calls", "was", "will", "can", "must",
}

_PATTERNS: dict[str, re.Pattern] = {
    "aadhaar_number": re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
    "phone_number": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),
    "mrn": re.compile(r"\bMRN\b\s*[:#-]?\s*[A-Za-z]*\d{3,}", re.I),
    "date_of_birth": re.compile(
        r"\b(?:DOB|D\.O\.B\.?|date of birth|born on)\b[^\n]{0,15}?\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}", re.I),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
}

_TITLE_NAME = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Smt|Shri|Master|Baby)\.?\s+((?:[A-Z]\.\s*)*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)")
_PATIENT_NAME = re.compile(r"\b[Pp]atient\s+(?:named\s+|name\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)")


def _name_hits(text: str) -> bool:
    for rx in (_TITLE_NAME, _PATIENT_NAME):
        for m in rx.finditer(text):
            words = [w.lower().strip(".") for w in m.group(1).split()]
            if not any(w in _NAME_STOP for w in words):
                return True
    return False


def detect_patient_data(text: str) -> list[str]:
    """Return sorted list of detected PII types (empty list == clean)."""
    found = {kind for kind, rx in _PATTERNS.items() if rx.search(text)}
    if _name_hits(text):
        found.add("person_name")
    return sorted(found)
