from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedChunk:
    section_no: str
    section_title: str
    page: int
    text: str            # body text, without the context header


@dataclass
class ParsedDoc:
    sop_id: str
    title: str
    version: str
    effective_date: str
    access_field: str
    access_level: str
    department: str
    source_path: str
    content_hash: str
    chunks: list[ParsedChunk] = field(default_factory=list)


@dataclass(frozen=True)
class StoredChunk:
    id: int
    sop_id: str
    version: str
    title: str
    effective_date: str
    access_level: str
    section_no: str
    section_title: str
    page: int
    text: str

    def context_header(self) -> str:
        return f"{self.sop_id} v{self.version} - {self.title} - section {self.section_no} {self.section_title}"


@dataclass(frozen=True)
class Citation:
    sop_id: str
    version: str
    title: str
    section: str
    section_title: str
    page: int


@dataclass
class Answer:
    answer: str
    refused: bool
    citations: list[Citation]
    index_generation: int
    reason: str = ""      # why refused (no_relevant_sop | llm_not_covered | ungrounded)
