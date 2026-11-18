# MediCare SOP Assistant
### AI-Powered Clinical SOP Knowledge Assistant using Retrieval-Augmented Generation (RAG)

<p align="center">
  <a href="https://medicare-sop-assistant.vercel.app/">
    <strong>🚀 OPEN LIVE APPLICATION</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://medicare-sop-assistant.onrender.com/docs">
    API Documentation
  </a>
  &nbsp; | &nbsp;
  <a href="https://github.com/PAWAN0207/-medicare-sop-assistant">
    Source Code
  </a>
</p>

---

## 📌 Overview

MediCare SOP Assistant is an AI-powered knowledge assistant designed to help healthcare staff retrieve information from Standard Operating Procedures (SOPs) using natural language questions.

Instead of manually searching through multiple PDF documents, staff can ask questions and receive answers grounded in relevant SOP content, along with source citations.

The application combines Retrieval-Augmented Generation (RAG), hybrid information retrieval, role-based access control, and relevance filtering to make document-based information retrieval more accessible and reliable.

**The primary objective is to provide relevant, traceable answers while avoiding unsupported responses when the available SOPs do not contain the requested information.**

## 🚀 Live Application

| Component | Link |
|---|---|
| Web Application | [Open MediCare SOP Assistant](https://medicare-sop-assistant.vercel.app/) |
| Backend API | [Open Backend](https://medicare-sop-assistant.onrender.com/) |
| API Documentation | [Swagger UI](https://medicare-sop-assistant.onrender.com/docs) |
| Health Check | [Check Backend Status](https://medicare-sop-assistant.onrender.com/healthz) |
| GitHub Repository | [View Source Code](https://github.com/PAWAN0207/-medicare-sop-assistant) |

*Note: The backend is hosted on a free-tier service. Initial requests may take longer if the service has been inactive.*

## ✨ Key Features

### 1. AI-Powered SOP Question Answering
- Ask questions using natural language.
- Retrieve relevant information from available SOP documents.
- Generate answers using retrieved document context.
- Return source citations to support answer verification.

### 2. Hybrid Information Retrieval
- Combines keyword-based BM25 retrieval with vector similarity search.
- Uses Reciprocal Rank Fusion (RRF) to combine retrieval rankings.
- Applies relevance checks before sending retrieved context to the language model.
- Retrieves only documents that the requesting staff member is permitted to access.

### 3. Role-Based Access Control (RBAC)
- Supports staff-specific access permissions.
- Applies access policies based on staff roles.
- Filters document retrieval according to permitted access levels.
- Prevents users from retrieving information outside their assigned access scope.

### 4. Source Citations
Answers include supporting source information such as:
- SOP identification.
- SOP version.
- Document title.
- Section and section title.
- Page number.

This allows staff to verify the information against the original procedure.

### 5. Responsible Answering and Refusal Handling
The system is designed to avoid generating unsupported answers.

It can refuse a question when:
- No relevant SOP information is retrieved.
- The available document context does not cover the question.
- The generated answer cannot be sufficiently grounded in retrieved evidence.

### 6. Privacy and Input Validation
- Detects potentially sensitive information in user questions.
- Includes checks for personally identifiable information (PII).
- Applies validation before processing requests.
- Keeps confidential source documents and sensitive evaluation inputs out of public documentation.

### 7. Document Ingestion and Indexing
- Extracts text from PDF SOP documents.
- Preserves document and page-level metadata.
- Splits extracted content into searchable chunks.
- Generates embeddings for retrieval.
- Stores indexed content and metadata in SQLite.

---

## 🏗️ System Architecture

```text
                 ┌──────────────────────┐
                 │         USER         │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   React Frontend     │
                 │   Hosted on Vercel   │
                 └──────────┬───────────┘
                            │
                       HTTPS / API
                            │
                            ▼
                 ┌──────────────────────┐
                 │    FastAPI Backend   │
                 │     Hosted on Render │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Authentication &    │
                 │ Access Policy (RBAC) │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    RAG Pipeline      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Hybrid Retrieval   │
                 │   BM25 + Vector      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Relevance Gate     │
                 │   & Context Builder  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Gemini LLM Adapter  │
                 │  Answer Generation  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Answer + Citations   │
                 │ or Refusal Response  │
                 └──────────────────────┘
```

## 🔄 RAG Workflow

The application follows two major processing stages.

### A. Document Ingestion

```text
SOP PDF Documents
       │
       ▼
PDF Text Extraction
       │
       ▼
Text Processing
       │
       ▼
Section and Chunk Creation
       │
       ▼
Embedding Generation
       │
       ▼
SQLite Index Storage
```

### B. Question Answering

```text
Staff Question
      │
      ▼
Input Validation
      │
      ▼
Staff Access Verification
      │
      ▼
Question Processing
      │
      ▼
Hybrid Retrieval
(BM25 + Vector Search)
      │
      ▼
Rank Fusion (RRF)
      │
      ▼
Relevance Validation
      │
      ├──────── No Relevant Context
      │                  │
      │                  ▼
      │             Safe Refusal
      │
      ▼
Relevant Context
      │
      ▼
Gemini Answer Generation
      │
      ▼
Citation Validation
      │
      ▼
Answer with Sources
```

## 🛠️ Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Frontend | React | User interface |
| Frontend Build | Vite | Frontend development and build |
| Backend | Python, FastAPI | API development and application logic |
| API Server | Uvicorn | ASGI application server |
| LLM | Google Gemini | Context-grounded answer generation |
| Embedding Model | gemini-embedding-001 | Document and query embeddings |
| Retrieval | BM25 + Vector Search | Hybrid information retrieval |
| Ranking | Reciprocal Rank Fusion | Combines retrieval rankings |
| Database | SQLite | Document chunks and index metadata |
| PDF Processing | pdfplumber | PDF text extraction |
| Testing | pytest | Automated testing |
| Deployment | Vercel | Frontend hosting |
| Deployment | Render | Backend hosting |
| Version Control | Git, GitHub | Source code management |

## 📊 Testing and Evaluation

Testing was performed across application components, retrieval behaviour, access permissions, and privacy-related validation.

| Testing Area | Result |
|---|---|
| Automated Test Suite | 74 Tests Passed |
| SOP Document Indexing | 15 Documents Indexed |
| Role-Based Access Testing | Passed |
| Retrieval Testing | Passed |
| Citation Validation | Passed |
| Refusal Handling | Passed |
| PII Detection Testing | Passed |
| API Testing | Passed |
| Live Deployment Testing | Passed |
| End-to-End Testing | Passed |

The results represent the completed project test runs and deployment verification.

## 📁 Project Structure

```text
sop-assistant/
│
├── data/
│   ├── sops/                  # SOP source documents (not published)
│   ├── sop_updates/           # Document update inputs
│   ├── eval_questions.csv     # Evaluation inputs
│   └── staff_users.csv        # Staff access data
│
├── sopassist/
│   ├── adapters/
│   │   ├── fake.py
│   │   └── openai_compat.py
│   │
│   ├── api/
│   │   └── app.py
│   │
│   ├── domain/
│   │   ├── access.py
│   │   ├── models.py
│   │   ├── pii.py
│   │   └── text.py
│   │
│   ├── eval/
│   │   ├── expectations.py
│   │   └── run_eval.py
│   │
│   ├── ingest/
│   │   ├── cli.py
│   │   ├── indexer.py
│   │   └── pdf_parser.py
│   │
│   ├── rag/
│   │   ├── prompts.py
│   │   ├── retriever.py
│   │   └── service.py
│   │
│   ├── store/
│   │   └── sqlite_store.py
│   │
│   ├── config.py
│   ├── container.py
│   ├── main.py
│   └── ports.py
│
├── tests/
│
├── docs/
│
├── requirements.txt
├── Dockerfile.render
└── README.md
```

*This is a simplified overview of the main application modules. Confidential data files and local runtime artifacts are intentionally excluded from the public repository.*

## ⚙️ Local Installation and Setup

### Prerequisites

- Python 3.12 recommended.
- Git.
- A Google Gemini API key with access to the configured models.
- A modern web browser.

### 1. Clone the repository

```bash
git clone https://github.com/PAWAN0207/-medicare-sop-assistant.git

cd -medicare-sop-assistant
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip

pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file using `.env.example` as a reference.

Typical configuration includes:

```env
PROVIDER=openai_compat

LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=your_gemini_api_key
LLM_MODEL=your_available_gemini_model

EMBED_MODEL=gemini-embedding-001

DATA_DIR=data
DB_PATH=var/sop_index.db
```

Use the exact variable names and supported values from the repository's `.env.example` and configuration module.

**Important:** Never commit your actual API key, `.env` file, confidential SOP documents, or staff records to GitHub.

### 5. Prepare the document index

Place authorized SOP PDFs inside the configured data directory.

Run the ingestion command:

```powershell
python -m sopassist.ingest.cli data/sops
```

### 6. Start the backend

```powershell
python -m uvicorn sopassist.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/healthz`

### 7. Run automated tests

```powershell
python -m pytest -v
```

## 🔐 Security and Data Handling

This project demonstrates document access controls, privacy-related input validation, and grounded question answering.

However, a publicly accessible demonstration should not be treated as a production healthcare system.

- Do not upload real patient records or personally identifiable information.
- Do not publish confidential SOP documents or staff records.
- Keep API keys and authentication secrets outside version control.
- Restrict access to the backend and its data in production.
- Use appropriate authentication, monitoring, rate limiting, and persistent storage before handling real organizational data.

## ⚠️ Important Disclaimer

MediCare SOP Assistant is an AI-assisted document retrieval and information support application.

It is not a replacement for professional medical judgement, clinical decision-making, official hospital policies, or emergency procedures.

Users should always verify important information against the applicable approved SOP and follow their organization's established protocols.

The live application is a portfolio demonstration, not a certified healthcare product.

## 🚀 Deployment

The application is deployed using separate frontend and backend services.

| Component | Hosting Platform |
|---|---|
| Frontend | Vercel |
| Backend API | Render |

The frontend communicates with the backend through HTTPS API requests.

Deployment configuration is managed through environment variables so that API endpoints, model settings, and application configuration can be changed without modifying source code.

## 🔮 Future Improvements

- Persistent production-grade database and vector storage.
- Advanced retrieval and reranking strategies.
- Document version management and change tracking.
- Expanded monitoring and observability.
- More comprehensive evaluation using real-world query patterns.
- Stronger production authentication and authorization.
- Improved deployment scalability and reliability.

## 👨‍💻 Author

**Pawan Ajay Prasad**

AI Engineer | Generative AI | Retrieval-Augmented Generation

- GitHub: https://github.com/PAWAN0207
- LinkedIn: https://www.linkedin.com/in/pawan-prasad-analyst/
- Portfolio: https://pawan0207.github.io/

---

<p align="center">
  <strong>Built to make healthcare SOP information easier to access, verify, and understand.</strong>
</p>