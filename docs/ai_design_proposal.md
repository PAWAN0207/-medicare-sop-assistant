# AI design proposal (saved as produced, not edited)

> **Provenance note (read first).** Tool: Claude (Anthropic), chat session on 18 Nov 2026. This document was generated in the
> *same working session* in which Claude also wrote the code, and it was written from the README brief only (the prompt below).
> It is therefore **not** a proposal obtained before any code existed; the chronology is disclosed rather than hidden. The review in
> `design_review.md` critiques it against what was actually built. Text below the line is unedited.

## Prompt
```
You are a senior AI engineer. Propose an architecture for the following client scenario. Cover ingestion/chunking, vector store,
REST API, access control, incremental re-indexing, caching, refusal + patient-data guard, evaluation, observability, deployment.
Be concrete about libraries and trade-offs. [Full text of README.md - MediCare Clinics SOP Knowledge Assistant - was pasted here]
```

---

## Proposed architecture

**Stack.** Python 3.12, FastAPI, LangChain for orchestration, ChromaDB (persistent client) as the vector store, OpenAI-compatible
embeddings (or Vertex AI `text-embedding`), Gemini Flash for generation, Redis for caching, Docker Compose, Cloud Run for deployment.

**Ingestion.** Load PDFs with PyPDF/`pdfplumber`, extract text per page, split with `RecursiveCharacterTextSplitter` (chunk size
1000 chars, overlap 200). Extract `sop_id`, `version`, `access` with regexes on page 1 and attach as metadata together with page
number. Tables are kept as plain text in the page.

**Document identity and re-indexing.** Identify each document by file name; store an MD5 of the file bytes in a `documents`
collection. On each snapshot run: new file name -> embed and add; same name, different MD5 -> delete the chunks whose
`source == filename` and re-add; file name missing from the folder -> delete its chunks. Log counts per run.

**Access control.** Map the `Access` field to a level using `access_policy.json`. At query time pass a Chroma `where` filter
`{"access_level": {"$in": allowed_levels}}` and additionally instruct the LLM in the system prompt to never reveal content
the user's role may not read.

**Q&A.** Embed the question, retrieve top-5 by cosine similarity (optionally hybrid with BM25 + reranker), build a prompt with the
chunks, call the LLM at temperature 0, and return answer plus citations taken from chunk metadata. If the best similarity is below
0.7, or if the LLM judges the context insufficient, answer "I don't know".

**Caching.** Semantic cache in Redis: embed the question, if an earlier question has cosine >= 0.95 return its stored answer (TTL 24 h).
On re-index, flush the cache.

**Patient-data guard.** Run a Presidio analyzer (or a short LLM classification prompt) over the question; if PII is found, redact the
entities and continue answering with the redacted question.

**Evaluation.** Run both CSVs through the API, use an LLM-as-judge to compare each answer with `expected_answer`, and report accuracy per
question type.

**Observability and ops.** Structured logs with a request id, OpenTelemetry traces, token and cost counters per LLM call, retry with
exponential backoff on provider errors, `/health` endpoint, OpenAPI via FastAPI, secrets via env vars / Secret Manager.

**Testing.** Pytest with a mocked LLM; integration test hitting a real Chroma instance.
