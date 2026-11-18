"""SQLite index: documents, chunks (+embeddings), answer cache, ingest runs.

Consistency model
- One DB file, WAL mode. A re-index is ONE write transaction (BEGIN IMMEDIATE): readers see the old
  snapshot or the new one, never a mix; a crash mid-way rolls back. BEGIN IMMEDIATE also serialises
  concurrent ingests.
- `generation` (meta table) increments in the same transaction as any content change. Cache keys include it.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from ..domain.models import StoredChunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
  sop_id TEXT PRIMARY KEY, title TEXT NOT NULL, version TEXT NOT NULL, effective_date TEXT NOT NULL,
  access_level TEXT NOT NULL, content_hash TEXT NOT NULL, source_path TEXT NOT NULL, indexed_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sop_id TEXT NOT NULL REFERENCES documents(sop_id) ON DELETE CASCADE,
  ord INTEGER NOT NULL, section_no TEXT NOT NULL, section_title TEXT NOT NULL, page INTEGER NOT NULL,
  text TEXT NOT NULL, access_level TEXT NOT NULL, embedding BLOB NOT NULL);
CREATE INDEX IF NOT EXISTS idx_chunks_access ON chunks(access_level);
CREATE TABLE IF NOT EXISTS answer_cache(
  key TEXT PRIMARY KEY, generation INTEGER NOT NULL, payload TEXT NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS ingest_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, finished_at REAL NOT NULL, generation INTEGER NOT NULL, report TEXT NOT NULL);
"""


class SqliteStore:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._shared: sqlite3.Connection | None = None
        if path == ":memory:":  # tests: one shared connection
            self._shared = self._open()
        with self.connect() as c:
            c.executescript(SCHEMA)
            c.execute("INSERT OR IGNORE INTO meta VALUES('generation','0')")
            c.commit()

    def _open(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        if self.path != ":memory:":
            c.execute("PRAGMA journal_mode=WAL")
        return c

    @contextmanager
    def connect(self):
        c = self._shared or self._open()
        try:
            yield c
        finally:
            if self._shared is None:
                c.close()

    # ---- reads -------------------------------------------------------------------------------
    def generation(self) -> int:
        with self.connect() as c:
            return int(c.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0])

    def embedder_id(self) -> str | None:
        with self.connect() as c:
            r = c.execute("SELECT value FROM meta WHERE key='embedder_id'").fetchone()
            return r[0] if r else None

    def documents(self) -> dict[str, dict]:
        with self.connect() as c:
            return {r["sop_id"]: dict(r) for r in c.execute("SELECT * FROM documents")}

    def read_allowed_chunks(self, levels: frozenset[str]) -> tuple[int, list[StoredChunk], np.ndarray]:
        """Access filter is applied in SQL: chunks of documents the caller may not read are never
        loaded into memory, so they cannot reach scoring or the prompt. Generation and chunks are
        read in ONE transaction -> consistent snapshot."""
        if not levels:
            return self.generation(), [], np.zeros((0, 0), dtype=np.float32)
        marks = ",".join("?" * len(levels))
        with self.connect() as c:
            c.execute("BEGIN")
            try:
                gen = int(c.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0])
                rows = c.execute(
                    f"""SELECT ch.id, ch.sop_id, d.version, d.title, d.effective_date, ch.access_level,
                               ch.section_no, ch.section_title, ch.page, ch.text, ch.embedding
                        FROM chunks ch JOIN documents d ON d.sop_id = ch.sop_id
                        WHERE ch.access_level IN ({marks}) ORDER BY ch.sop_id, ch.ord""",
                    sorted(levels)).fetchall()
            finally:
                c.execute("COMMIT")
        chunks = [StoredChunk(r["id"], r["sop_id"], r["version"], r["title"], r["effective_date"],
                              r["access_level"], r["section_no"], r["section_title"], r["page"], r["text"])
                  for r in rows]
        mat = (np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
               if rows else np.zeros((0, 0), dtype=np.float32))
        return gen, chunks, mat

    # ---- cache -------------------------------------------------------------------------------
    def cache_get(self, key: str) -> dict | None:
        with self.connect() as c:
            r = c.execute("SELECT payload FROM answer_cache WHERE key=? AND expires_at>?",
                          (key, time.time())).fetchone()
            return json.loads(r[0]) if r else None

    def cache_put(self, key: str, generation: int, payload: dict, ttl_s: int) -> None:
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO answer_cache VALUES(?,?,?,?)",
                      (key, generation, json.dumps(payload), time.time() + ttl_s))

    def cache_size(self) -> int:
        with self.connect() as c:
            return c.execute("SELECT COUNT(*) FROM answer_cache").fetchone()[0]

    # ---- ingest ------------------------------------------------------------------------------
    def last_runs(self, n: int = 5) -> list[dict]:
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM ingest_runs ORDER BY id DESC LIMIT ?", (n,))]
