"""python -m sopassist.ingest.cli <snapshot_folder> [--dry-run] [--rebuild] [--force]"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..config import Settings
from ..container import build_providers
from ..domain.access import AccessPolicy
from ..errors import AppError
from ..logging_setup import setup_logging
from ..store.sqlite_store import SqliteStore
from .indexer import Indexer, format_report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Index a full SOP library snapshot (incremental, idempotent).")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    ap.add_argument("--rebuild", action="store_true", help="re-embed every document (e.g. new embedding model)")
    ap.add_argument("--force", action="store_true", help="allow withdrawing a large share of the library")
    a = ap.parse_args(argv)
    s = Settings()
    setup_logging("WARNING")
    try:
        _, embedder = build_providers(s)
        report = Indexer(SqliteStore(s.db_path), embedder, AccessPolicy.load(s.policy_path),
                         s.max_removal_fraction).run(a.folder, rebuild=a.rebuild, force=a.force, dry_run=a.dry_run)
    except AppError as e:
        print(f"ERROR [{e.code}]: {e}", file=sys.stderr)
        return 1
    print(format_report(report) + ("\n  (dry run: nothing written)" if report.get("dry_run") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
