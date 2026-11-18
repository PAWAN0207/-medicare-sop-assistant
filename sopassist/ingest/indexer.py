"""Snapshot-based incremental indexer.

Document identity = SOP id from the PDF header (stable across file renames).
Change detection  = content hash over normalised extracted content + header metadata
                    (NOT file bytes: re-exported PDFs differ in bytes/timestamps; NOT file name: renamed files).
The folder is treated as the full library: anything indexed but absent from the snapshot is withdrawn.
Safety: parse + embed first (no DB writes); then apply everything in ONE transaction."""
from __future__ import annotations

import array
import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Callable

from ..domain.access import AccessPolicy
from ..domain.models import ParsedDoc
from ..errors import IngestError
from ..ports import Embedder
from ..store.sqlite_store import SqliteStore
from .pdf_parser import parse_pdf

log = logging.getLogger("sopassist.ingest")


def _context_text(d: ParsedDoc, c) -> str:
    """Text that is embedded: includes SOP id/title/section so each chunk is self-describing."""
    return f"{d.sop_id} {d.title} - {c.section_no}. {c.section_title}\n{c.text}"


class Indexer:
    def __init__(self, store: SqliteStore, embedder: Embedder, policy: AccessPolicy,
                 max_removal_fraction: float = 0.5, fault_hook: Callable[[str], None] | None = None):
        self.store, self.embedder, self.policy = store, embedder, policy
        self.max_removal_fraction = max_removal_fraction
        self._fault = fault_hook or (lambda stage: None)   # tests inject crashes here

    def run(self, folder: Path, *, rebuild: bool = False, force: bool = False, dry_run: bool = False) -> dict:
        folder = Path(folder)
        pdfs = sorted(folder.rglob("*.pdf"))
        if not pdfs:
            raise IngestError(f"No PDFs found in {folder}; refusing to treat an empty folder as 'withdraw everything'")

        # 1. parse everything; any failure aborts the whole run (a half-read library must not withdraw docs)
        docs: dict[str, ParsedDoc] = {}
        errors: list[str] = []
        for p in pdfs:
            try:
                d = parse_pdf(p, self.policy)
            except IngestError as e:
                errors.append(str(e))
                continue
            if d.sop_id in docs:
                errors.append(f"Duplicate SOP id {d.sop_id}: {Path(docs[d.sop_id].source_path).name} and {p.name}")
                continue
            docs[d.sop_id] = d
        if errors:
            raise IngestError("Snapshot rejected, index unchanged: " + "; ".join(errors))

        # 2. embedder consistency
        stored_emb = self.store.embedder_id()
        if stored_emb and stored_emb != self.embedder.embedder_id and not rebuild:
            raise IngestError(f"Index was built with embedder {stored_emb!r}, now {self.embedder.embedder_id!r}. "
                              "Re-run with --rebuild to re-embed everything.")

        # 3. plan
        current = self.store.documents()
        plan = {"added": [], "updated": [], "unchanged": [], "removed": [], "renamed": [], "moved": []}
        for sid, d in sorted(docs.items()):
            old = current.get(sid)
            if old is None:
                plan["added"].append(sid)
            elif old["content_hash"] != d.content_hash or rebuild:
                plan["updated"].append(sid)
            else:
                plan["unchanged"].append(sid)
                if old["source_path"] != d.source_path:
                    plan["moved"].append(sid)          # path changed (folder and/or file name): metadata only
                    if Path(old["source_path"]).name != Path(d.source_path).name:
                        plan["renamed"].append(sid)
        plan["removed"] = sorted(set(current) - set(docs))
        if (current and len(plan["removed"]) > max(1, self.max_removal_fraction * len(current))
                and not force):
            raise IngestError(f"Refusing to withdraw {len(plan['removed'])} of {len(current)} documents "
                              "(looks like a wrong/partial folder). Use --force if intended.")

        report = {
            "snapshot": str(folder),
            "added": [f"{s} v{docs[s].version}" for s in plan["added"]],
            "updated": [f"{s} v{current[s]['version']} -> v{docs[s].version}"
                        if current[s]["version"] != docs[s].version else f"{s} v{docs[s].version} (content changed)"
                        for s in plan["updated"]],
            "removed": [f"{s} v{current[s]['version']}" for s in plan["removed"]],
            "unchanged": plan["unchanged"],
            "renamed_files_only": [f"{s}: {Path(current[s]['source_path']).name} -> {Path(docs[s].source_path).name}"
                                   for s in plan["renamed"]],
        }
        to_embed = plan["added"] + plan["updated"]
        report["chunks_embedded"] = sum(len(docs[s].chunks) for s in to_embed)
        content_change = bool(to_embed or plan["removed"])
        report["changed"] = content_change
        if dry_run:
            report["dry_run"] = True
            return report

        # 4. embed outside any DB transaction (slow + external; a crash here changes nothing)
        vectors: dict[str, list[list[float]]] = {}
        for s in to_embed:
            d = docs[s]
            vectors[s] = self.embedder.embed([_context_text(d, c) for c in d.chunks])
        self._fault("after_embed")

        # 5. apply atomically
        t0 = time.time()
        with self.store.connect() as c:
            c.execute("BEGIN IMMEDIATE")        # single writer; waits (timeout) if another ingest is running
            try:
                gen = int(c.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0])
                for s in plan["removed"] + plan["updated"]:
                    c.execute("DELETE FROM chunks WHERE sop_id=?", (s,))
                    if s in plan["removed"]:
                        c.execute("DELETE FROM documents WHERE sop_id=?", (s,))
                self._fault("mid_apply")
                for s in to_embed:
                    d = docs[s]
                    c.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?,?,?)",
                              (s, d.title, d.version, d.effective_date, d.access_level, d.content_hash,
                               d.source_path, t0))
                    for i, (ch, vec) in enumerate(zip(d.chunks, vectors[s])):
                        c.execute("INSERT INTO chunks(sop_id,ord,section_no,section_title,page,text,access_level,embedding)"
                                  " VALUES(?,?,?,?,?,?,?,?)",
                                  (s, i, ch.section_no, ch.section_title, ch.page, ch.text, d.access_level,
                                   array.array("f", vec).tobytes()))
                for s in plan["moved"]:
                    c.execute("UPDATE documents SET source_path=? WHERE sop_id=?", (docs[s].source_path, s))
                if content_change:
                    gen += 1
                    c.execute("UPDATE meta SET value=? WHERE key='generation'", (str(gen),))
                    c.execute("DELETE FROM answer_cache WHERE generation < ?", (gen,))   # purge stale answers
                    c.execute("INSERT OR REPLACE INTO meta VALUES('embedder_id',?)", (self.embedder.embedder_id,))
                    c.execute("INSERT INTO ingest_runs(finished_at,generation,report) VALUES(?,?,?)",
                              (time.time(), gen, json.dumps(report)))
                c.execute("COMMIT")
            except BaseException:
                c.execute("ROLLBACK")
                raise
        report["generation"] = gen
        log.info("ingest finished", extra={"report": report})
        return report


def format_report(r: dict) -> str:
    lines = [f"Snapshot: {r['snapshot']}"]
    for k in ("added", "updated", "removed", "renamed_files_only"):
        lines.append(f"  {k:>18}: {', '.join(r[k]) if r[k] else '-'}")
    lines.append(f"  {'unchanged':>18}: {len(r['unchanged'])} documents (not re-embedded)")
    lines.append(f"  {'chunks embedded':>18}: {r['chunks_embedded']}")
    lines.append(f"  {'index generation':>18}: {r.get('generation', 'unchanged') if r['changed'] else 'unchanged (no-op run)'}")
    return "\n".join(lines)
