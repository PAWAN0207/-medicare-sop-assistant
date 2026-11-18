import csv

import pytest

from sopassist.domain.pii import detect_patient_data

from .conftest import DATA


def test_pack_inputs():
    rows = list(csv.DictReader(open(DATA / "pii_test_inputs.csv")))
    assert len(rows) == 5
    for r in rows:
        found = detect_patient_data(r["input"])
        assert bool(found) == (r["expected_guard_result"] != "no flag"), r["input"]


@pytest.mark.parametrize("text,kind", [
    ("Patient Ramesh Kumar has fever", "person_name"),
    ("MRN 448812 needs a retest", "mrn"),
    ("Aadhaar 452188901234 on file", "aadhaar_number"),
    ("call +91 98480 22113", "phone_number"),
    ("patient DOB 12/04/1961", "date_of_birth"),
    ("email her at asha.k@example.com", "email"),
])
def test_detects_each_type(text, kind):
    assert kind in detect_patient_data(text)


@pytest.mark.parametrize("text", [
    "What is the procedure for a needle-stick injury?",
    "Patient Registration steps for walk-in patients?",
    "What does SOP-04 v3.0 say about OH-05?",
    "Refund up to Rs 1,500 for billing errors?",
    "Slots are 15 minutes, max 14 per session",
    "What is the policy for patients without ID?",
])
def test_no_false_positives(text):
    assert detect_patient_data(text) == []


def test_returns_types_never_values():
    out = detect_patient_data("Patient Ramesh Kumar, MRN 448812")
    assert all(isinstance(x, str) and "Ramesh" not in x and "448812" not in x for x in out)
