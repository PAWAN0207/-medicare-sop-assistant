import pytest

from sopassist.domain.access import AccessPolicy
from sopassist.errors import IngestError, UnknownUser
from sopassist.ingest.pdf_parser import parse_pdf

from .conftest import ORIGINAL, UPDATE


def test_role_levels(policy):
    assert policy.levels_for_role("front_desk") == {"all"}
    assert policy.levels_for_role("nurse") == {"all", "clinical"}
    assert policy.levels_for_role("hr") == {"all", "hr"}
    assert policy.levels_for_role("clinic_manager") == {"all", "clinical", "hr"}


def test_unknown_role_sees_nothing(policy):
    assert policy.levels_for_role("intern") == frozenset()


def test_unknown_access_field_fails_closed(policy):
    with pytest.raises(IngestError):
        policy.level_for_field("Board members only")


def test_unknown_user(users):
    with pytest.raises(UnknownUser):
        users.get("U9999")


def test_header_metadata_comes_from_document(policy):
    d = parse_pdf(next(ORIGINAL.glob("SOP-10*")), policy)
    assert (d.sop_id, d.version, d.access_level) == ("SOP-10", "3.1", "clinical")   # multi-line Access cell
    d = parse_pdf(next(ORIGINAL.glob("SOP-13*")), policy)
    assert d.access_level == "hr"


def test_table_rows_stay_whole(policy):
    d = parse_pdf(next(ORIGINAL.glob("SOP-10*")), policy)
    sec4 = next(c for c in d.chunks if c.section_no == "4")
    assert "Tube cap colour: Light blue; Additive: Sodium citrate" in sec4.text


def test_revision_history_is_not_indexed(policy):
    for pdf in list(ORIGINAL.glob("*.pdf")) + list(UPDATE.glob("*.pdf")):
        d = parse_pdf(pdf, policy)
        blob = " ".join(c.text for c in d.chunks)
        assert "Superseded" not in blob and "Revision history" not in blob, pdf.name
    d = parse_pdf(next(UPDATE.glob("SOP-02*")), policy)
    assert "20%" not in " ".join(c.text for c in d.chunks)   # old value only lived in revision history/old file


def test_renamed_file_same_identity_and_hash(policy):
    old = parse_pdf(next(ORIGINAL.glob("SOP-05*")), policy)
    new = parse_pdf(next(UPDATE.glob("SOP-05*")), policy)
    assert old.source_path != new.source_path
    assert (old.sop_id, old.content_hash) == (new.sop_id, new.content_hash)


def test_changed_version_changes_hash(policy):
    a = parse_pdf(next(ORIGINAL.glob("SOP-02*")), policy)
    b = parse_pdf(next(UPDATE.glob("SOP-02*")), policy)
    assert a.content_hash != b.content_hash


def test_corrupt_pdf_rejected(tmp_path, policy):
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(IngestError):
        parse_pdf(bad, policy)
