"""PDF -> ParsedDoc. Identity (SOP id), version and access come from the document header, never the file name.

Tables are rendered row-by-row as 'Header: value; ...' so a table row stays one retrievable fact.
The revision-history table/section is deliberately NOT indexed: it contains old values
('20% -> 25%', 'Superseded') that would resurrect stale facts."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pdfplumber

from ..domain.access import AccessPolicy
from ..domain.models import ParsedChunk, ParsedDoc
from ..errors import IngestError

_RUNNING = re.compile(r"^(MediCare Clinics\s+SOP-\d+\s*\|.*|Internal document\. Uncontrolled.*|Approved by:.*)$")
_TITLE = re.compile(r"^(SOP-\d+):\s*(.+)$")
_SECTION = re.compile(r"^(\d+)\.\s+([A-Z].{0,80})$")
_CID = re.compile(r"\(cid:\d+\)")
MAX_CHUNK_CHARS = 1200


def _fix_glyphs(s: str | None) -> str:
    """Some PDFs use a symbol font whose bullets pdfplumber cannot map ('(cid:127)'); show them as a bullet."""
    return _CID.sub("\u2022", s or "")


def _clean(s: str | None) -> str:
    return " ".join(_fix_glyphs(s).split())


def _render_table(rows: list[list[str | None]]) -> str:
    rows = [[_clean(c) for c in r] for r in rows if any(_clean(c) for c in r)]
    if len(rows) < 2:
        return "\n".join(" | ".join(r) for r in rows)
    head, body = rows[0], rows[1:]
    return "\n".join("; ".join(f"{h}: {v}" for h, v in zip(head, r)) for r in body)


def _page_blocks(page) -> list[str]:
    """Text of one page in reading order with tables replaced by rendered rows.
    Header-metadata and revision-history tables are returned with a marker prefix."""
    tables = sorted(page.find_tables(), key=lambda t: t.bbox[1])
    blocks: list[str] = []
    y = 0.0
    for t in tables:
        top, bottom = t.bbox[1], t.bbox[3]
        if top > y:
            blocks.append(_fix_glyphs(page.crop((0, y, page.width, top)).extract_text()))
        rows = t.extract()
        first = [_clean(c) for c in rows[0]] if rows else []
        if first[:1] == ["Department"]:
            blocks.append("@@META@@" + "\n".join("|".join(_clean(c) for c in r) for r in rows))
        elif first[:3] == ["Version", "Date", "Change"]:
            blocks.append("@@REVISION@@")
        else:
            blocks.append(_render_table(rows))
        y = bottom
    if y < page.height:
        blocks.append(_fix_glyphs(page.crop((0, y, page.width, page.height)).extract_text()))
    return blocks


def parse_pdf(path: Path, policy: AccessPolicy) -> ParsedDoc:
    path = Path(path)
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:  # corrupt / not a pdf
        raise IngestError(f"{path.name}: cannot open PDF ({type(e).__name__})")
    with pdf:
        sop_id = title = None
        meta: dict[str, str] = {}
        sections: list[dict] = []          # {no, title, page, lines}
        cur: dict | None = None
        in_revision = False
        for pno, page in enumerate(pdf.pages, start=1):
            for block in _page_blocks(page):
                if block.startswith("@@META@@"):
                    for row in block[8:].splitlines():
                        cells = row.split("|")
                        for i in range(0, len(cells) - 1, 2):
                            meta[cells[i].strip().lower()] = cells[i + 1].strip()
                    continue
                if block == "@@REVISION@@":
                    in_revision = True
                    continue
                for raw in block.splitlines():
                    line = raw.strip()
                    if not line or _RUNNING.match(line):
                        continue
                    if line == "Revision history":
                        in_revision = True
                        continue
                    m = _TITLE.match(line)
                    if m and sop_id is None:
                        sop_id, title = m.group(1), m.group(2).strip()
                        continue
                    if sop_id is None or in_revision:
                        continue
                    if line.startswith(("Department ", "Version ", "Access ")) and cur is None:
                        continue   # header rows already captured from the table
                    if cur is None and not _SECTION.match(line):
                        continue
                    s = _SECTION.match(line)
                    if s:
                        cur = {"no": s.group(1), "title": s.group(2).strip(), "page": pno, "lines": []}
                        sections.append(cur)
                    elif cur is not None:
                        cur["lines"].append(line)
        if not sop_id:
            raise IngestError(f"{path.name}: no 'SOP-NN: title' line found")
        for needed in ("version", "access"):
            if not meta.get(needed):
                raise IngestError(f"{path.name}: header field {needed!r} missing")
        level = policy.level_for_field(meta["access"])
        chunks = _chunk(sections)
        if not chunks:
            raise IngestError(f"{path.name}: no sections found")
        digest = hashlib.sha256()
        for part in (sop_id, title, meta["version"], meta.get("effective date", ""), level):
            digest.update(part.encode() + b"\x1f")
        for c in chunks:
            digest.update(f"{c.section_no}\x1f{c.section_title}\x1f{c.page}\x1f{c.text}\x1e".encode())
        return ParsedDoc(sop_id=sop_id, title=title, version=meta["version"],
                         effective_date=meta.get("effective date", ""), access_field=meta["access"],
                         access_level=level, department=meta.get("department", ""),
                         source_path=str(path), content_hash=digest.hexdigest(), chunks=chunks)


def _chunk(sections: list[dict]) -> list[ParsedChunk]:
    """One chunk per section (SOP sections are small, self-contained procedures).
    Oversized sections are split on line boundaries, each part keeping the section heading."""
    out: list[ParsedChunk] = []
    for s in sections:
        body = "\n".join(s["lines"]).strip()
        if not body:
            continue
        if len(body) <= MAX_CHUNK_CHARS:
            out.append(ParsedChunk(s["no"], s["title"], s["page"], body))
            continue
        part: list[str] = []
        size = 0
        for line in s["lines"]:
            if size + len(line) > MAX_CHUNK_CHARS and part:
                out.append(ParsedChunk(s["no"], s["title"], s["page"], "\n".join(part)))
                part, size = [], 0
            part.append(line)
            size += len(line) + 1
        if part:
            out.append(ParsedChunk(s["no"], s["title"], s["page"], "\n".join(part)))
    return out