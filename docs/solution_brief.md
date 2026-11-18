# MediCare SOP Assistant
### AI-Powered SOP Knowledge Assistant

**Prepared for:** Head of Operations
**Solution Type:** Retrieval-Augmented Generation (RAG) Proof of Concept

---

## 1. The Problem

Clinic staff often spend valuable time searching through multiple Standard Operating Procedure (SOP) documents to find the correct instructions.

When old and updated documents are stored together, staff may accidentally follow outdated procedures. This can lead to inconsistent decisions, delays and operational risks.

## 2. Proposed Solution

MediCare SOP Assistant is an AI-powered assistant that helps clinic staff find answers directly from their approved SOP documents.

Staff can ask questions in natural language and receive clear answers with references to the original documents.

The system is designed to:

- Answer questions using available SOP documents.
- Display SOP ID, version, section and page references.
- Refuse questions when sufficient supporting information is unavailable.
- Restrict document access according to staff permissions.
- Block detected patient identifiers before retrieval and AI processing.
- Process new, modified and withdrawn SOP documents.

## 3. How the System Works

The application follows a Retrieval-Augmented Generation (RAG) workflow.

**Step 1 – Document Processing**
The system reads PDF documents and extracts their text and section information.

**Step 2 – Document Indexing**
Extracted content is divided into meaningful chunks. The system stores document metadata and vector embeddings for searching.

**Step 3 – Access Verification**
Before retrieval, the system checks the requesting user's access permissions.

**Step 4 – Hybrid Search**
The system combines keyword-based BM25 search and vector similarity search. Reciprocal Rank Fusion combines the results to identify relevant SOP sections.

**Step 5 – Answer Generation**
The language model generates an answer using the retrieved SOP content.

**Step 6 – Citation Display**
The response includes references to the source SOP, version, section and page.

**Step 7 – Document Updates**
When documents change or are withdrawn, the index is updated and outdated cached answers are invalidated.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, Vite |
| Language Model | Google Gemini |
| Embedding Model | Gemini Embedding |
| Vector Search | NumPy-based cosine similarity |
| Keyword Search | BM25 |
| Result Ranking | Reciprocal Rank Fusion |
| Database | SQLite |
| PDF Processing | pdfplumber |
| Testing | Pytest |
| Deployment Packaging | Docker |

## 5. Security and Data Protection

Security is an important part of the application.

- Role-based access filtering restricts which SOP documents a user can retrieve.
- Restricted document content is excluded from the language model context.
- Detected patient identifiers are blocked before retrieval and AI processing.
- Cache entries are isolated using access information and index generation.
- Request IDs help identify and trace API requests.
- API credentials are managed through environment variables rather than committed to source control.

**Production requirement:** Secure staff authentication, centralized authorization, managed secrets and appropriate network controls must be completed before real clinic deployment.

## 6. Testing and Evaluation Results

The proof of concept has undergone automated backend testing, semantic retrieval evaluation and frontend manual testing.

| Test Area | Result |
|---|---|
| Automated backend test suite | 74 passed, 0 failed |
| Semantic retrieval evaluation | 12/12 expected retrieval checks passed |
| Unanswerable questions | 3 cases inspected |
| Post-update role-mixed evaluation | 8/8 passed |
| Patient-data protection evaluation | 5/5 passed |
| Frontend manual testing | Core question-answer, citation and refusal flows tested |

The automated tests cover:

- Role-based access control.
- Patient information protection.
- Document indexing and updates.
- Cache isolation and invalidation.
- Citation metadata.
- Unsupported question handling.
- API endpoints and error handling.

The semantic retrieval evaluation checks whether expected SOP content appears in the retrieved results. It does not independently prove that every generated answer is correct.

The application has also been connected to the Gemini API and tested through its frontend. Further live-model evaluation is required before production use.

## 7. Cost and Infrastructure Considerations

The application uses a lightweight architecture to keep infrastructure requirements manageable.

The main operating costs will depend on:

- Language model API usage.
- Embedding generation during document indexing.
- Backend hosting.
- Document and database storage.
- Number of staff and daily questions.

Caching can reduce repeated model calls. Incremental indexing can also reduce unnecessary embedding requests when only a few SOP documents change.

Actual monthly costs should be measured during a pilot using real usage data and current provider pricing.

## 8. Risks and Mitigation

| Risk | Mitigation |
|---|---|
| Incorrect or unsupported answers | Retrieval checks, citations and refusal handling |
| Patient information exposure | PII detection and blocking before AI processing |
| Unauthorized document access | Role-based filtering and production authentication |
| Outdated SOP information | Document version tracking and transactional index updates |
| Increased document volume | Evaluate a managed database and dedicated vector database when required |
| Model provider dependency | Keep provider configuration separate from core application logic |

## 9. Recommended Next Steps

1. Complete further live-model answer-quality evaluation.
2. Integrate secure staff authentication and authorization.
3. Deploy the application in a controlled environment.
4. Conduct a pilot with a small group of clinic staff.
5. Collect feedback and review unanswered questions.
6. Measure actual API, hosting and storage costs.
7. Evaluate scalability and monitoring requirements before wider deployment.

## 10. Conclusion

MediCare SOP Assistant demonstrates how Retrieval-Augmented Generation can make clinic SOP information easier to access while maintaining document-level permissions, source citations and refusal controls.

The current implementation provides a working proof of concept with a functional frontend, FastAPI backend, hybrid retrieval, document update handling and automated testing.

Additional authentication, security validation, operational monitoring and pilot testing are necessary before the system can be used in a real clinical environment.
