import shutil
import threading

import pytest

from sopassist.errors import IngestError
from sopassist.ingest.indexer import Indexer
from sopassist.store.sqlite_store import SqliteStore

from .conftest import ORIGINAL, UPDATE, CountingEmbedder


def chunk_rows(store):
    with store.connect() as c:
        return [tuple(r) for r in c.execute("SELECT sop_id, ord, section_no, text FROM chunks ORDER BY sop_id, ord")]


def test_first_run_adds_all(indexer, store):
    r = indexer.run(ORIGINAL)
    assert len(r["added"]) == 15 and not r["updated"] and not r["removed"]
    assert store.generation() == 1


def test_second_run_is_noop_and_free(indexer, store, embedder):
    indexer.run(ORIGINAL)
    before, gen = chunk_rows(store), store.generation()
    n = embedder.texts_embedded
    r = indexer.run(ORIGINAL)
    assert not r["changed"] and r["chunks_embedded"] == 0
    assert embedder.texts_embedded == n          # zero embedding cost
    assert chunk_rows(store) == before and store.generation() == gen


def test_update_snapshot_diff(indexer, store, embedder):
    indexer.run(ORIGINAL)
    n = embedder.texts_embedded
    r = indexer.run(UPDATE)
    assert sorted(x.split()[0] for x in r["added"]) == ["SOP-16", "SOP-17"]
    assert sorted(x.split()[0] for x in r["updated"]) == ["SOP-02", "SOP-08", "SOP-11"]
    assert [x.split()[0] for x in r["removed"]] == ["SOP-15"]
    assert len(r["unchanged"]) == 11
    assert any("SOP-05" in x for x in r["renamed_files_only"])          # rename detected, not re-embedded
    assert embedder.texts_embedded - n == r["chunks_embedded"]
    assert "SOP-05" not in " ".join(r["updated"] + r["added"])


def test_no_stale_chunks_after_update(indexer, store):
    indexer.run(ORIGINAL)
    indexer.run(UPDATE)
    docs = store.documents()
    assert "SOP-15" not in docs and docs["SOP-02"]["version"] == "2.4" and docs["SOP-11"]["version"] == "2.0"
    with store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM chunks WHERE sop_id='SOP-15'").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM chunks WHERE sop_id NOT IN (SELECT sop_id FROM documents)").fetchone()[0] == 0
    text = " ".join(r[3] for r in chunk_rows(store) if r[0] == "SOP-02")
    assert "25%" in text and "20%" not in text
    assert sum(1 for d in docs if d == "SOP-05") == 1                    # not duplicated


def test_update_is_idempotent(indexer, store):
    indexer.run(ORIGINAL)
    indexer.run(UPDATE)
    rows, gen = chunk_rows(store), store.generation()
    r = indexer.run(UPDATE)
    assert not r["changed"] and r["chunks_embedded"] == 0
    assert chunk_rows(store) == rows and store.generation() == gen


@pytest.mark.parametrize("stage", ["after_embed", "mid_apply"])
def test_crash_leaves_index_untouched(store, embedder, policy, stage):
    Indexer(store, embedder, policy).run(ORIGINAL)
    before, gen = chunk_rows(store), store.generation()

    def boom(s):
        if s == stage:
            raise RuntimeError("simulated crash")
    with pytest.raises(RuntimeError):
        Indexer(store, embedder, policy, fault_hook=boom).run(UPDATE)
    assert chunk_rows(store) == before and store.generation() == gen      # all-or-nothing
    assert store.documents()["SOP-15"]["version"] == "1.1"
    Indexer(store, embedder, policy).run(UPDATE)                          # recovers by simply re-running
    assert store.documents()["SOP-02"]["version"] == "2.4"


def test_readers_never_see_a_mix(tmp_path, policy):
    """While re-indexing runs, concurrent readers see SOP-02 v2.3 or v2.4 chunk sets, never both/neither."""
    store = SqliteStore(str(tmp_path / "i.db"))
    ix = Indexer(store, CountingEmbedder(), policy)
    ix.run(ORIGINAL)
    seen, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            _, chunks, _ = store.read_allowed_chunks(frozenset({"all", "clinical", "hr"}))
            seen.append(frozenset((c.sop_id, c.version) for c in chunks if c.sop_id in ("SOP-02", "SOP-11", "SOP-15")))
    t = threading.Thread(target=reader)
    t.start()
    ix.run(UPDATE)
    stop.set()
    t.join()
    old = frozenset({("SOP-02", "2.3"), ("SOP-11", "1.2"), ("SOP-15", "1.1")})
    new = frozenset({("SOP-02", "2.4"), ("SOP-11", "2.0")})
    assert seen and all(s in (old, new) for s in seen)


def test_duplicate_sop_id_rejects_snapshot(tmp_path, indexer, store):
    indexer.run(ORIGINAL)
    snap = tmp_path / "snap"
    shutil.copytree(UPDATE, snap)
    shutil.copy(next(UPDATE.glob("SOP-02*")), snap / "SOP-02_copy.pdf")
    gen = store.generation()
    with pytest.raises(IngestError, match="Duplicate"):
        indexer.run(snap)
    assert store.generation() == gen


def test_empty_or_wrong_folder_never_withdraws_everything(tmp_path, indexer, store):
    indexer.run(ORIGINAL)
    with pytest.raises(IngestError):
        indexer.run(tmp_path)                                              # empty folder
    partial = tmp_path / "p"
    partial.mkdir()
    shutil.copy(next(ORIGINAL.glob("SOP-01*")), partial)
    with pytest.raises(IngestError, match="Refusing to withdraw"):
        indexer.run(partial)
    assert len(store.documents()) == 15
    assert indexer.run(partial, force=True)["removed"]


def test_one_bad_pdf_aborts_whole_snapshot(tmp_path, indexer, store):
    indexer.run(ORIGINAL)
    snap = tmp_path / "s"
    shutil.copytree(UPDATE, snap)
    (snap / "broken.pdf").write_bytes(b"garbage")
    with pytest.raises(IngestError):
        indexer.run(snap)
    assert store.documents()["SOP-15"]                                     # nothing withdrawn


def test_embedder_change_requires_rebuild(store, embedder, policy):
    Indexer(store, embedder, policy).run(ORIGINAL)

    class Other(CountingEmbedder):
        embedder_id = "other-model"
    with pytest.raises(IngestError, match="--rebuild"):
        Indexer(store, Other(), policy).run(ORIGINAL)
    r = Indexer(store, Other(), policy).run(ORIGINAL, rebuild=True)
    assert r["chunks_embedded"] > 0 and store.embedder_id() == "other-model"


def test_dry_run_writes_nothing(indexer, store):
    indexer.run(ORIGINAL)
    gen = store.generation()
    r = indexer.run(UPDATE, dry_run=True)
    assert r["dry_run"] and r["updated"] and store.generation() == gen
