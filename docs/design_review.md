# Design Review and Architecture Decision Records

## 1. Introduction

This document reviews the AI-generated architecture proposal in `docs/ai_design_proposal.md` and compares it with the architecture implemented in the MediCare SOP Assistant.

The original proposal was generated during the same working session as the implementation. It was not a pre-implementation design document. This chronology is disclosed in the original proposal.

The purpose of this review is to explain which proposed ideas were retained, which were changed, and why the final implementation better addresses the requirements and risks identified in the supplied SOP document pack.

The review considers document updates, access control, patient-data protection, retrieval quality, caching, reliability and operating cost.

## 2. Weaknesses and Risks Identified in the Original Proposal

| No. | Original proposal | Risk identified | Final implementation |
|---|---|---|---|
| 1 | Use file names as document identity and MD5 of file bytes for change detection. | Renaming an SOP could incorrectly appear as a document removal followed by a new addition. PDF metadata changes could also trigger unnecessary re-embedding. | Document identity is derived from the SOP ID in the PDF header. Changes are detected using a hash of normalized extracted content and relevant metadata. |
| 2 | Use a fixed 1,000-character chunk size with 200-character overlap. | Fixed-size splitting can separate procedure steps and table rows. Revision history may also introduce outdated information into retrieval. | Section-aware chunking is used. Tables are preserved row by row, and revision-history content is excluded from indexing. |
| 3 | Delete and re-add documents individually during re-indexing. | A failure during the operation could leave incomplete or inconsistent document data. Queries might also encounter old and new versions together. | Documents are parsed and embedded before database changes. Updates, removals and generation changes are applied in a single database transaction. |
| 4 | Use semantic caching with a cosine similarity threshold of 0.95. | Similar-looking questions may require different answers. Responses could also be shared across users with different access permissions. | An exact normalized-question cache key includes access levels, index generation and model-related configuration. |
| 5 | Detect patient information using an LLM or redact it before answering. | Sending unredacted patient information to an external provider creates a privacy risk. Redaction may also miss sensitive values. | A deterministic local PII guard blocks detected sensitive input before retrieval, caching or LLM processing. |
| 6 | Rely partly on prompt instructions to prevent restricted information from being disclosed. | Prompt instructions alone cannot enforce authorization. A malicious or misleading question could attempt to bypass them. | Access filtering is applied during database retrieval. Restricted content is excluded before it reaches the LLM. |
| 7 | Use LangChain and ChromaDB as core application dependencies. | Tightly coupling business logic to a framework or vector database makes testing and future changes more difficult. | The implementation uses separate application interfaces for LLM and embedding providers, with SQLite as the persistence layer. |
| 8 | Use one global similarity threshold of 0.7 and an LLM judge for evaluation. | Similarity scores can vary across embedding models. LLM-based evaluation also introduces cost and makes offline testing more difficult. | A deterministic relevance gate, a not-covered response contract and citation validation are used. Offline evaluation provides repeatable regression checks. |

## 3. Important Design Decisions

### 3.1 Document Identity and Change Detection

The original proposal uses the file name as the document identity.

This approach is not reliable when an SOP is renamed. The supplied update snapshot includes a renamed SOP-05, which should not be treated as an entirely new document when its identity and content remain unchanged.

The final implementation uses the SOP ID extracted from the PDF header as the document identity.

A normalized content hash is used to detect meaningful changes. Relevant document metadata is also included in the change detection process.

This approach helps avoid unnecessary embedding calls and ensures that document updates are handled consistently.

### 3.2 Section-Aware Chunking

Fixed-size text splitting is simple, but it does not always preserve the meaning of operational procedures.

For example, a table containing tube colours, additives and collection instructions should remain understandable when retrieved.

The final implementation uses section-aware chunking and preserves table information row by row.

Revision-history content is excluded because it may contain superseded information that should not be returned as current operational guidance.

### 3.3 Transactional Re-indexing

The original proposal suggests deleting and re-adding individual documents.

The problem is that a failure between these operations could leave the index incomplete.

The final implementation separates the process into two stages:

1. Parse and embed the documents before changing the active index.
2. Apply additions, updates, removals and generation changes inside a single database transaction.

This design helps ensure that readers see a consistent index rather than a mixture of old and new document versions.

### 3.4 Access Control

Access control is enforced during retrieval rather than relying only on instructions sent to the LLM.

The application determines which document access levels are permitted for the requesting user.

Only permitted chunks are retrieved and passed to the answer-generation stage.

This reduces the risk of restricted information appearing in the LLM context.

### 3.5 Patient-Data Protection

The original proposal considers redacting patient information and continuing with the request.

The final implementation takes a stricter approach.

Detected PII results in the request being blocked. The application returns identifier types rather than exposing the detected values.

The guard runs before retrieval, caching and LLM processing.

This reduces the chance of sensitive information being sent to an external model provider or stored in cached responses.

The current deterministic approach has limitations, particularly around detecting names without sufficient contextual indicators. More advanced local NER or DLP support could improve detection in a future version.

---

## 4. Architecture Decision Records (ADRs)

### ADR-1: SOP Identity and Content-Based Change Detection

**Status:** Accepted

**Context**

The SOP library can contain renamed, updated and withdrawn documents. File names are not reliable identifiers because a document may change its file name without changing its actual identity.

**Options considered**

- Option A: File name and file-byte hash.
- Option B: SOP ID only.
- Option C: SOP ID and normalized content hash.
- Option D: SOP ID and version number only.

**Decision**

Option C was selected.

The SOP ID extracted from the document header identifies the document. A hash of normalized extracted content and relevant metadata determines whether the document requires updating.

**Reasoning**

- Renaming a document does not automatically make it a new SOP.
- PDF metadata changes should not unnecessarily trigger re-embedding.
- Content changes should be detected even if the document version number is unchanged.
- Duplicate SOP IDs can be rejected instead of creating ambiguous records.

**Consequences**

The document must be parsed before the system can determine whether it has changed.

This introduces some parsing overhead but avoids unnecessary embedding operations.

A parser or normalization change may alter content hashes, in which case a rebuild may be required.

**Strongest argument against this decision**

Version-based change detection is simpler and easier to understand. However, it depends on document authors updating version information correctly whenever content changes.

---

### ADR-2: Atomic Snapshot Updates Using SQLite Transactions

**Status:** Accepted

**Context**

Staff should not receive a mixture of old and new SOP versions when documents are updated.

A failed indexing operation should not leave the active index partially updated.

**Options considered**

- Option A: Individual delete-and-add operations.
- Option B: A single database transaction.
- Option C: Build a separate index and switch to it after validation.

**Decision**

Option B was selected.

Document parsing and embedding happen before the database write operation. The final changes are applied in one transaction.

The transaction updates document records, chunks, index generation and stale cache entries.

**Reasoning**

- Failed transactions can be rolled back.
- Readers are protected from partially applied updates.
- Document updates and cache invalidation remain consistent.
- The design is simple to run locally and does not require another database service.

**Consequences**

SQLite is suitable for the current proof of concept and its relatively small document collection.

Large indexing operations may hold the write lock for longer periods.

Embedding work completed before a failed transaction may need to be repeated.

**Strongest argument against this decision**

A blue-green indexing approach could provide a separate validation stage and allow rollback to the previous index after deployment.

That approach may become more useful if the document library or deployment requirements grow significantly.

---

### ADR-3: Exact Cache Keys with Access Levels and Index Generation

**Status:** Accepted

**Context**

The assistant may receive repeated questions. Caching can reduce response time and external LLM costs.

However, returning a stale answer or sharing a response across different permission levels can create serious problems.

**Options considered**

- Option A: Semantic caching using embedding similarity.
- Option B: Exact normalized-question caching with permission and generation information.
- Option C: No caching.

**Decision**

Option B was selected.

The cache key uses the normalized question and relevant application configuration, including:

- Permitted access levels.
- Index generation.
- Prompt version.
- LLM identifier.
- Embedder identifier.
- Search mode.

The cache is stored in SQLite with a time-to-live policy.

**Reasoning**

- Different access levels should not share responses.
- An updated SOP should not leave old answers available.
- Similar but meaningfully different questions should not collide.
- Cache invalidation should be linked to index generation.

**Consequences**

Exact matching is less effective for paraphrased questions than semantic caching.

However, it provides more predictable behaviour and avoids the risks associated with approximate question matching.

Refusals may be cached, while errors and PII-blocked requests are not cached.

**Strongest argument against this decision**

Semantic caching could improve the cache hit rate when staff ask the same question in different ways.

It could be considered later with strict permission-aware cache keys and additional answer validation.

---

### ADR-4: SQLite and In-Process Vector Search

**Status:** Accepted for the current proof of concept

**Context**

The project needs persistent document storage, vector retrieval, metadata filtering and caching.

The implementation also needs to run locally without requiring multiple external infrastructure services.

The inspected index contains 74 chunks and uses 3072-dimensional embeddings.

**Options considered**

- Option A: ChromaDB or Qdrant.
- Option B: PostgreSQL with pgvector.
- Option C: SQLite with stored embeddings, NumPy-based vector similarity and BM25 retrieval.

**Decision**

Option C was selected for the current implementation.

SQLite stores document metadata, chunks, embeddings and cache information. Vector similarity is calculated using NumPy, while BM25 supports keyword-based retrieval.

The results are combined using Reciprocal Rank Fusion (RRF).

**Reasoning**

- SQLite reduces infrastructure and deployment complexity.
- Document metadata and cache information can be managed in the same persistence layer.
- The current document collection is small enough for a straightforward retrieval implementation.
- Hybrid retrieval helps with exact operational terms such as SOP identifiers, emergency codes and medical procedure references.
- Offline tests can run without a separately hosted vector database.

**Consequences**

The implementation is suitable for a small, single-instance proof of concept.

It does not provide distributed vector search, horizontal scaling or the operational capabilities of a dedicated vector database.

Performance should be benchmarked with a larger document collection before making production-scale claims.

**Strongest argument against this decision**

Qdrant or PostgreSQL with pgvector would provide a clearer migration path for larger collections and multi-instance deployments.

If the document library or concurrent user requirements increase significantly, a dedicated vector database or managed database should be evaluated.

---

## 5. Additional Implementation Decisions

| Decision | Reason |
|---|---|
| Block detected patient information instead of redacting and continuing. | Reduces the risk of exposing sensitive information to external services. |
| Exclude revision history from indexing. | Prevents superseded instructions from being retrieved as current guidance. |
| Apply access filtering before LLM processing. | Ensures restricted document content is not included in the model context. |
| Refuse unsupported questions before generation. | Reduces unnecessary model calls and unsupported answers. |
| Validate citations against retrieved document metadata. | Prevents the model from inventing document references. |
| Use hybrid BM25 and vector retrieval. | Supports both semantic questions and exact SOP terminology. |
| Use environment variables for provider configuration and secrets. | Avoids hardcoding credentials in application code. |
| Use request IDs and structured API errors. | Makes application failures easier to investigate. |
| Use retry and timeout handling for provider calls. | Improves resilience against temporary external service failures. |
| Keep offline test providers. | Allows repeatable testing without requiring paid API calls. |

---

## 6. Testing and Evidence

The implementation includes automated tests for the major design decisions.

The latest recorded automated test execution completed with 74 passing tests and no failures.

Important test coverage includes:

- Role-based retrieval restrictions.
- PII detection and blocking.
- Prevention of cross-role cache leakage.
- Citation structure validation.
- Refusal of unsupported questions.
- Document update and withdrawal handling.
- Transaction rollback and concurrent-reader consistency.
- API validation and error handling.
- Provider timeout and retry behaviour.

The project also includes offline evaluation results and a separate semantic retrieval evaluation report.

These tests provide evidence for the implemented behaviour, but they do not replace production security testing, load testing or a full clinical validation process.

---

## 7. Known Limitations and Future Improvements

The current implementation is a proof of concept designed around the supplied fictional SOP dataset.

The following improvements should be considered before production deployment:

1. **Authentication:** Replace demonstration user identification with a production identity provider and secure authentication.
2. **PII detection:** Evaluate more advanced local NER or DLP models to improve detection of patient names and other sensitive information.
3. **Database scalability:** Evaluate PostgreSQL and pgvector or Qdrant if document volume and concurrent usage increase.
4. **Observability:** Add centralized monitoring, distributed tracing and operational dashboards.
5. **Evaluation:** Expand testing with additional paraphrases, adversarial questions and human-reviewed answer-quality assessments.
6. **Deployment security:** Add production-grade secret management, network restrictions and appropriate access controls.
7. **Performance:** Benchmark retrieval latency, concurrent requests and indexing time using a larger SOP collection.
8. **Backup and recovery:** Establish automated database backups and a documented restoration process.

---

## 8. Final Conclusion

The final architecture does not follow the original AI-generated proposal blindly.

Several ideas were retained, including metadata-based access filtering, hybrid retrieval, structured citations, environment-based configuration and provider retry handling.

Other decisions were changed to address specific risks in the supplied document pack.

The most important changes are document identity based on SOP IDs, section-aware chunking, transactional indexing, permission-aware caching and blocking detected patient information before external processing.

The final implementation prioritizes correctness, predictable behaviour, privacy protection and low infrastructure cost for the current proof of concept.

The architecture can be extended as the document collection, user base and operational requirements grow.