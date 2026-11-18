"""Machine-checkable pass criteria per eval question (derived from the 'expected_answer' column).

PASS rules
  answerable / conflict : not refused AND every expected (SOP, section[, version]) is cited AND every fact regex matches
  unanswerable          : refused AND zero citations
  after-update rows     : as above, plus must_not_cite / forbidden-text checks for stale or restricted content
Facts are a *minimal* set of the critical details (numbers, names), not full-answer completeness - judging full
completeness needs a human or an LLM judge (listed as a limitation)."""
from __future__ import annotations

# (sop_id, {sections} or None, version or None)
ORIGINAL = {
    "Q01": dict(cite=[("SOP-04", {"2", "3"}, None)], facts=[r"2 minutes", r"2 hours"]),
    "Q02": dict(cite=[("SOP-05", {"2"}, None)], facts=[r"red bag"]),
    "Q03": dict(cite=[("SOP-02", {"2"}, None)], facts=[r"15 minutes", r"\b14\b"]),
    "Q04": dict(cite=[("SOP-06", {"4"}, None)], facts=[r"do not use", r"1 hour"]),
    "Q05": dict(cite=[("SOP-10", {"4"}, None)], facts=[r"light blue", r"lavender"]),
    "Q06": dict(cite=[("SOP-08", {"4"}, None)], facts=[r"1,000"]),
    "Q07": dict(cite=[("SOP-07", {"2"}, None)], facts=[r"code pink", r"child"]),
    "Q08": dict(cite=[("SOP-12", {"5"}, None)], facts=[r"1 hour", r"data protection officer"]),
    "Q09": dict(cite=[("SOP-15", {"4"}, None)], facts=[r"schedule x"]),
    "Q10": dict(cite=[("SOP-12", {"4"}, None)], facts=[r"21"]),
    "Q11": dict(refuse=True),
    "Q12": dict(refuse=True),
    "Q13": dict(refuse=True),
    "Q14": dict(cite=[("SOP-04", {"3"}, None), ("SOP-11", {"3"}, None)], facts=[r"2 hours", r"24 hours"]),
    "Q15": dict(cite=[("SOP-06", {"3"}, None), ("SOP-09", {"4"}, None)], facts=[r"twice", r"once daily"]),
}

AFTER_UPDATE = {
    "U01": dict(cite=[("SOP-02", {"3"}, "2.4")], facts=[r"25\s*(%|percent)"], forbidden=[r"\b20\s*(%|percent)"],
                not_cite=[("SOP-02", "2.3")]),
    "U02": dict(cite=[("SOP-08", {"4"}, "2.1")], facts=[r"1,500"], forbidden=[r"up to rs 1,000 for billing"],
                not_cite=[("SOP-08", "2.0")]),
    "U03": dict(cite=[("SOP-04", {"3"}, None), ("SOP-11", {"3"}, "2.0")], facts=[r"2 hours", r"24 hours"],
                not_cite=[("SOP-11", "1.2")]),
    "U04": dict(refuse=True, not_cite=[("SOP-15", None)]),
    "U05": dict(cite=[("SOP-16", {"2"}, None)], facts=[r"rescue"]),
    "U06": dict(refuse=True, not_cite=[("SOP-17", None)], forbidden=[r"50,000"]),
    "U07": dict(cite=[("SOP-17", {"3"}, None)], facts=[r"50,000"]),
    "U08": dict(cite=[("SOP-05", {"2"}, None)], facts=[r"red bag"], single_version_of="SOP-05"),
}

PII_EXPECTED = {
    "flag: name + MRN": {"person_name", "mrn"},
    "flag: Aadhaar number": {"aadhaar_number"},
    "flag: phone number": {"phone_number"},
    "no flag": set(),
    "flag: name + DOB": {"person_name", "date_of_birth"},
}
