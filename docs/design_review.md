# Design review of the AI's proposal, and ADRs

Reference: `docs/ai_design_proposal.md`. Everything below was checked against the actual pack (e.g. the update snapshot renames SOP-05,
withdraws SOP-15, and bumps SOP-02/08/11) and, where possible, backed by a test.

## Weaknesses and risks found in the proposal (and what was done instead)

| # | Weakness / risk in the proposal | Why it breaks on *this* data | What I did instead |
|---|---|---|---|
| 1 | **File name as document identity**, MD5 of file bytes as change detector | SOP-05 is renamed in the snapshot with unchanged content: by file name it would be "SOP-05 removed + a new document added" (re-embedded, and during the swap duplicated). File bytes are also unstable (re-exports change PDF metadata/timestamps) so unchanged docs would be re-embedded. | Identity = **SOP id from the PDF header**; change = **hash of normalised content + header metadata**. Rename is detected, reported, and costs 0 embeddings (`test_update_snapshot_diff`). |
| 2 | **Fixed 1000/200 character splitter on raw page text** | Cuts procedures mid-step and splits table rows (SOP-05 colour table, SOP-10 order of draw) across chunks. Worse, the **revision-history table** says "increased from 20% to 25%" / "Superseded" - indexing it resurrects exactly the stale facts U01/U02 test for. | Section-aware chunks (one per numbered section, split only if >1200 chars), tables rendered row-by-row ("Tube cap colour: Light blue; Additive: ..."), revision history never indexed (`test_revision_history_is_not_indexed`). |
| 3 | **Per-file delete-then-add** re-indexing | Not atomic: a crash between delete and add leaves a document missing; a query during the swap can see old+new chunks (SOP-11 v1.2 *and* v2.0 -> the "conflict" that U03 says must be gone). Adding/removing across several files has no common consistent point. | Parse + embed first (no writes), then **one transaction** applying all adds/updates/removals, bumping a `generation`, purging stale cache. Crash tests and a concurrent-reader test prove no mixed state. |
| 4 | **Semantic cache (cosine >= 0.95) + flush on re-index** | Near-identical questions with different answers collide ("refund up to Rs 1,000" vs "above Rs 10,000" differ by a few tokens); the proposal's cache is not keyed by role, so an HR answer from SOP-13 can be served to a front-desk user; flush-on-reindex races with in-flight requests that then write an old answer *after* the flush. | **Exact normalised-question key** + access-level set + generation + prompt/model/embedder ids. A racing request writes under the old generation key which nobody reads. (ADR-3) |
| 5 | **PII guard via LLM / redact-and-continue** | Sending the raw patient name/MRN to an external LLM *is* processing patient information, the thing the client forbids. Redaction that misses one token leaks it anyway; and the redacted question is cached and logged. | **Deterministic local guard** (regex rules), **block** instead of redact, return only identifier *types*, never log or echo values, guard runs before cache/retrieval/LLM (`test_pii_blocked_before_llm_cache_and_retrieval`). Limitation: names need a title/"patient" cue; NER/DLP is the next step. |
| 6 | **"Instruct the LLM not to reveal restricted content"** as part of access control | A prompt rule is bypassable ("ignore previous instructions"). The README says restricted text must never reach the context. | Filter lives in the SQL that loads candidates; rows of other levels are never loaded. A spy LLM test asserts restricted text never appears in any prompt, including for an injection-style question. The proposal's metadata filter itself was kept. |
| 7 | **LangChain + Chroma wired through the domain** | Violates the requirement that business rules not depend on a provider/framework/DB, and is slow to test offline. | Own ports (`LLMClient`, `Embedder`), fake adapters, SQLite store; only `container.py` selects adapters. |
| 8 | **Single global similarity threshold (0.7) for "I don't know"**, LLM-as-judge for everything | Cosine scale differs per embedding model, so 0.7 is arbitrary; and an LLM judge cannot be run offline or reproduced. Nothing stops an ungrounded answer with fake citations. | Three layers: deterministic idf-weighted term-coverage gate (no LLM call spent on out-of-scope questions), `NOT_COVERED` contract, and **citation validation** (answer with no valid `[C#]` marker becomes a refusal; citations are built from chunk metadata, not LLM text). Eval uses deterministic pass rules; LLM judge listed as future work. |

## What I kept and why
- **Metadata filter at retrieval for access** (the right place; I just moved it into SQL and dropped the prompt reliance).
- **Hybrid BM25 + vector** idea: SOP content has exact tokens ("OH-05", "Code Pink", "Schedule X") where keyword match helps; implemented with RRF.
- **Citations from metadata** (sop_id, version, section, page) rather than model text.
- **Structured logs + request id, retry/backoff on provider 429/5xx**, FastAPI/OpenAPI, env-based config, Docker Compose.
- **Evaluation by question type through the real API path** - but with deterministic pass rules.

## ADR-1: Document identity and change detection  *(overrules the AI)*
- **Context.** The snapshot is a full library; file names are not stable (SOP-05 renamed); withdrawn SOPs just vanish.
- **Options.** (a) file name + file-byte hash (AI's proposal); (b) SOP id only (always re-embed or trust version); (c) **SOP id + content hash**; (d) SOP id + `version` header as the change signal.
- **Decision.** (c): identity from the header SOP id, change detection from a hash of normalised extracted content and header fields (version, effective date, access level, title, sections/pages).
- **Why not the others.** (a) false remove+add on rename, re-embeds on re-export. (b) re-embeds everything or misses edits. (d) trusts humans: a content edit without a version bump would be silently missed (this pack's SOP-05 keeps v2.2 while the file changes name, and a careless author could edit text and forget the version).
- **Consequences.** Needs parsing before diffing (cheap compared with embedding). Two files with the same SOP id are ambiguous -> the whole snapshot is rejected rather than guessing. Hash includes page/section, so a layout change that moves a section re-embeds that document (safe direction, small cost). A change to normalisation code changes hashes -> `--rebuild`.
- **Strongest argument for the opposite.** Hashing normalised text still depends on parser stability; a parser upgrade changes every hash. Version-header diffing is simpler, human-auditable, and matches how the client already governs documents.

## ADR-2: Atomic snapshot swap in one transaction with a generation counter  *(overrules the AI)*
- **Context.** Staff must never get a mix of old and new chunks, even if re-indexing crashes; the library will reach 200+ SOPs.
- **Options.** (a) per-file delete-then-add in a vector DB (AI); (b) **single DB transaction** holding documents, chunks and vectors; (c) blue/green: build a complete new index, flip a pointer.
- **Decision.** (b) on SQLite (WAL): all embedding happens before the write; the write is one `BEGIN IMMEDIATE` transaction that replaces chunks, removes withdrawn docs, bumps `generation` and purges older cache rows.
- **Consequences.** Readers get snapshot isolation for free; a crash rolls back; `BEGIN IMMEDIATE` serialises concurrent ingests; re-run = recovery. Cost: embeddings are recomputed if the process dies after embedding but before commit (cheap at this size). Index and metadata must live in the same store (they do).
- **Strongest argument for the opposite.** Blue/green (c) gives instant rollback to the previous version and lets you smoke-test the new index with the eval set *before* it serves traffic; one big transaction holds the write lock longer as the library grows and has no rollback after commit.

## ADR-3: Cache design - exact key including access levels and index generation  *(overrules the AI)*
- **Context.** ~2,000 questions/day with many repeats; wrong cached answers are worse than slow answers (stale SOP, other role's content).
- **Options.** (a) semantic cache, cosine >= 0.95, flush on re-index (AI); (b) **exact normalised-question key** with levels + generation + model ids; (c) no cache.
- **Decision.** (b). Key = sha256(normalised question, sorted access levels, generation, prompt version, LLM id, embedder id, search mode); persisted in SQLite so it survives restarts; TTL 24 h; stale-generation rows purged in the re-index transaction. Refusals are cached, errors and PII blocks never are.
- **Consequences.** Zero risk of collision between near-identical questions; levels (not user id) keep hit rate high while never sharing across visibility sets; generation in the key makes invalidation structural rather than a flush that can race. Cost: paraphrases miss (hit rate lower than semantic), cache grows per distinct phrasing.
- **Strongest argument for the opposite.** Staff ask the same thing in many wordings; a semantic cache with a *strict* threshold and the same key dimensions could roughly double the hit rate and save LLM cost and latency.

## ADR-4: SQLite + in-process vector math instead of Chroma/pgvector
- **Context.** 15-200+ SOPs (~1,500 chunks at most), 2,000 q/day, one-command run, atomic swap needed.
- **Options.** (a) Chroma/Qdrant; (b) Postgres + pgvector; (c) **SQLite with embeddings as BLOBs and numpy cosine + in-memory BM25 over the permitted rows**.
- **Decision.** (c) for the PoC behind a small store class; ~1,500 x 768 floats is a few MB, brute force is exact and ~ms.
- **Consequences.** One file, transactional with metadata and cache, trivial to run and test; but single-node, no ANN, whole permitted set is read per query. Migration path: pgvector (same transactional story) when >50k chunks or multi-instance.
- **Strongest argument for the opposite.** A real vector DB demonstrates production fit and offers filtering/ANN/horizontal scale; SQLite will have to be thrown away for multi-instance Cloud Run.

## Other decisions (short)
| Decision | Reason |
|---|---|
| Block, don't redact, patient data | redaction can leak, and keeps patient data out of cache/logs/LLM |
| Revision history excluded from the index | it contains superseded values by design |
| Refuse before calling the LLM when the gate fails | saves cost, removes a hallucination path for out-of-scope questions |
| Snapshot guardrails (empty folder, duplicate id, >50% withdrawals, unparsable file abort the run) | a wrong folder must not silently withdraw the library |
