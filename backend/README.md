# CodeImpact — FastAPI Backend

**Tagline:** "Don't Just Find Dead Code. Understand What Happens When You Remove It."  
**Role:** Person 4 — Backend Orchestration, Integration & AI.

---

## 1. Purpose

The CodeImpact backend coordinates repository analysis for JavaScript and TypeScript projects. It orchestrates:
- **Repository Retrieval & Static Analysis (Person 2 - OM_2):** Git clone, Knip, and jscpd execution.
- **Dependency Graph & Impact Analysis (Person 3 - SAMAR_3):** Madge import mapping, circular dependency detection, and risk scoring.
- **AI Explanations & Safe Recommendations (Person 4 - TANUJA_4):** Evidence-grounded Gemini explanations and verification steps.
- **Audit Report Generation (Person 4 - TANUJA_4):** Markdown reports (Phase 5).

---

## 2. Directory Structure

```text
backend/
├── API_CONTRACT.md          # Authoritative shared API contract
├── README.md                # This setup and run guide
├── requirements.txt         # Pinned Python dependencies (including google-genai)
├── .env.example             # Environment template with Gemini variables
├── app/
│   ├── main.py              # FastAPI entry point, CORS, exception handlers
│   ├── core/
│   │   └── config.py        # Pydantic Settings application configuration
│   ├── api/
│   │   ├── repositories.py  # POST /api/repositories/analyse
│   │   ├── analyses.py      # GET status, findings, detail, graph, POST explain, GET report
│   │   ├── ai.py            # AI route reference
│   │   └── reports.py       # Markdown report download routes (Phase 5)
│   ├── schemas/
│   │   ├── common.py        # ErrorDetail, ErrorResponse models
│   │   ├── analysis.py      # AnalysisRequest, AnalysisStatus, metrics models
│   │   ├── evidence.py      # EvidenceItem, TestCandidate, FindingImpact
│   │   ├── finding.py       # FindingItem, FindingDetail, FindingsListResponse
│   │   ├── graph.py         # GraphNode, GraphEdge, GraphResponse
│   │   └── ai.py            # ExplainRequest, ExplainResponse
│   ├── adapters/            # Teammate engine adapters (clean boundaries)
│   │   ├── base.py          # Adapter protocols
│   │   ├── repository_adapter.py    # Repo retrieval & safe workspace cleanup
│   │   ├── static_analysis_adapter.py # Person 2 (Knip/jscpd) adapter
│   │   └── dependency_impact_adapter.py # Person 3 (Madge) adapter
│   ├── services/
│   │   ├── analysis_store.py # Thread-safe in-memory job & findings store
│   │   ├── orchestrator.py  # Background pipeline coordinator
│   │   ├── reports/         # Deterministic Markdown report generator (Phase 5)
│   │   │   └── report_generator.py # Assembly, formatting, and RFC attachment naming
│   │   └── ai/              # Gemini AI service and prompt templates
│   │       ├── gemini_service.py   # Google GenAI client and generation logic
│   │       └── prompt_templates.py # Grounded prompt builder & deterministic fallback
│   └── utils/               # Subprocess and filesystem utilities
└── tests/
    ├── test_health.py           # Health check probe test
    ├── test_analysis_request.py # URL validation and 202 Accepted test
    ├── test_schemas.py          # Schema constraint and serialization tests
    ├── test_api.py              # Basic API route tests
    ├── test_analysis_store.py   # In-memory store operations & metrics tests
    ├── test_lifecycle.py        # Status lifecycle transitions tests
    ├── test_orchestrator.py     # Background pipeline & failure recovery tests
    ├── test_analyses_api.py     # Analyses, findings, and graph API tests
    ├── test_ai_prompt.py        # Grounded prompt building and fallback tests
    ├── test_ai_service.py       # Gemini client mocking, parsing, and errors
    ├── test_ai_endpoint.py      # POST /explain endpoint integration tests
    ├── test_report_generator.py # Markdown report generator formatting & determinism tests
    └── test_report_endpoint.py  # GET /api/analyses/{id}/report download endpoint tests
```

---

## 3. Analysis Lifecycle & Background Orchestration

1. **Submission:** Client sends `POST /api/repositories/analyse` with `{ "repository_url": "...", "branch": "main" }`.
2. **Acceptance:** Request is validated, a unique `analysis_id` (`an_<id>`) is generated, initial record is persisted in `AnalysisStore` with status `queued`, and a background pipeline task is scheduled. The client immediately receives `202 Accepted`.
3. **Execution Pipeline (`AnalysisOrchestrator`):**
   - **Stage 1 (`cloning`):** Calls `RepositoryAdapter` to clone into an isolated temporary workspace. If retrieval fails, the job transitions to `failed` and records the error.
   - **Stage 2 (`static_analysis`):** Calls `StaticAnalysisAdapter` to run Knip and jscpd. Tool output is normalized into `FindingItem` models.
   - **Stage 3 (`dependency_graph`):** Calls `DependencyImpactAdapter` to run Madge, constructing directed graph nodes, edges (`source -> target`), cycles, and enriching findings with impact metrics and test candidates.
   - **Stage 4 (`completion`):** Calculates summary metrics from actual outputs. Status is set to:
     - `completed`: All tools ran successfully.
     - `partial`: At least one tool failed (e.g., jscpd or Madge), but usable findings or graph data were produced.
     - `failed`: No usable results produced or fatal pipeline error.
4. **Safe Workspace Cleanup:** The orchestrator guarantees workspace deletion in a `finally` block, verifying the target path resides strictly inside the system temporary directory.
5. **In-Memory Store:** For hackathon MVP simplicity, all job state and findings are stored in-memory in `AnalysisStore` using thread-safe synchronization (`threading.RLock`). *Note: State is maintained for the lifetime of the backend process and resets upon server restart.*

---

## 4. Gemini AI Explanations & Cleanup Recommendations

- **Endpoint:** `POST /api/analyses/{analysis_id}/explain` with `{ "finding_id": "f_..." }`.
- **Grounded Context:** Prompts incorporate the finding's file path, line numbers, symbols, source tool evidence items, review risk, and dependency impact (direct dependents, test suites, and cycle membership).
- **Core Guidelines:**
  - Never guarantees code is safe to delete. Uses cautious phrasing ("potentially unused", "candidate for review").
  - Identifies plausible false-positive scenarios (dynamic imports, runtime reflection, framework conventions).
  - Outlines concrete verification steps for developers before making changes.
  - Transparently acknowledges static analysis limitations.
- **Structured Schema:** Uses `google-genai` JSON schema enforcement matching `ExplainResponse`.
- **Graceful Degradation:**
  - The backend and `/health` probe start normally even without a `GEMINI_API_KEY`.
  - When unconfigured, `/explain` returns an informative `503 Service Unavailable` with error code `AI_SERVICE_UNAVAILABLE`.
  - An evidence-grounded deterministic fallback generator is available when offline or during API quota limits.

---

## 5. Markdown Audit Report Generation (Phase 5)

- **Endpoint:** `GET /api/analyses/{analysis_id}/report`
- **Response Format:** Downloadable Markdown (`text/markdown; charset=utf-8`) with `Content-Disposition: attachment; filename="CodeImpact_Report_{repo}_{analysis_id}.md"`.
- **Report Architecture:**
  - Strictly deterministic compilation: given identical stored analysis data and timestamp, it outputs byte-for-byte identical markdown.
  - Zero external calls: does not call Gemini, does not re-run analyzers, does not clone repositories.
  - Evidence-grounded: never claims code is safe to delete, clearly flags dynamic import caveats, and compiles pre-cleanup verification checklists.
  - Gracefully handles missing/partial tools, cycles, and AI explanation caches.
- **Report Structure:**
  1. Title & Header (Repository, branch, commit, analysis ID, generation timestamp)
  2. Executive Summary (Status, tool coverage, high-risk items, partial completion notes)
  3. Analysis Metadata (Start/end timestamps, duration, files analyzed, tool breakdown, errors)
  4. Findings Metrics Table (Categorized by type, review risk, severity, confidence, and source analyzer)
  5. Detailed Findings & Evidence (Sorted by risk level `high -> medium -> low`, with line numbers, symbols, tool evidence, and cached AI explanations)
  6. Dependency Graph & Structural Impact (Total nodes/edges, high-impact hub files, detected circular dependency chains)
  7. Pre-Cleanup Verification Checklist & Analysis Limitations (Unit test verification, dynamic dispatch warnings, and non-destructive refactoring tips)

---

## 6. Endpoints Available

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check probe | `200 OK` |
| `POST` | `/api/repositories/analyse` | Start analysis job in background | `202 Accepted` |
| `GET` | `/api/analyses/{analysis_id}` | Polling endpoint for job status & summary metrics | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/findings` | Paginated, filterable findings explorer | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/findings/{finding_id}` | Detailed finding evidence & test candidates | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/graph` | Directed dependency graph & detected cycles | `200 OK` (or `404`) |
| `POST` | `/api/analyses/{analysis_id}/explain` | Grounded AI explanation & recommendations | `200 OK` (or `404`, `503`) |
| `GET` | `/api/analyses/{analysis_id}/report` | Downloadable Markdown audit report | `200 OK` (or `404`) |

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 7. Environment Variables (.env)

The backend reads configuration settings from a `.env` file located in `backend/.env` via Pydantic Settings ([`backend/app/core/config.py`](file:///C:/Users/ASUS/Desktop/DeadCode-Detective/backend/app/core/config.py)).

To initialize your local environment:
```bash
cp .env.example .env
```

### Configuration Reference Table

| Variable | Default Value | Required | Description |
|---|---|---|---|
| `APP_NAME` | `"CodeImpact API"` | No | Application display title shown in Swagger UI and API health probes. |
| `APP_ENV` / `ENVIRONMENT` | `development` | No | Deployment environment (`development`, `staging`, `production`). |
| `API_PREFIX` | `/api` | No | Base routing prefix for all REST API endpoints. |
| `HOST` / `BACKEND_HOST` | `127.0.0.1` | No | Server interface binding IP (`0.0.0.0` for all interfaces). |
| `PORT` / `BACKEND_PORT` | `8000` | No | Server HTTP listening port. |
| `FRONTEND_ORIGIN` | `http://localhost:3000,http://localhost:5173` | No | Comma-separated list of allowed origins for browser CORS policy. |
| `GEMINI_API_KEY` | *(None)* | Optional | Google Gemini API key from [Google AI Studio](https://aistudio.google.com/) for live AI explanations. If omitted, the system gracefully falls back to deterministic AST explanations. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | No | Model identifier for AI explanations (`gemini-2.5-flash`, `gemma-4-it`). |
| `MAX_REPO_SIZE_MB` | `200.0` | No | Maximum allowed repository disk footprint (MB) before retrieval aborts. |
| `MAX_FILE_COUNT` | `10000` | No | Maximum non-ignored file count permitted in target repositories. |
| `SUBPROCESS_TIMEOUT_SECONDS` | `180` | No | Hard process execution timeout for Git, Knip, jscpd, and Madge subprocesses. |

### Example `.env` File

```ini
# CodeImpact Backend Environment Configuration
APP_NAME="CodeImpact API"
APP_ENV=development
ENVIRONMENT=development
API_PREFIX=/api
HOST=127.0.0.1
PORT=8000
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_ORIGIN=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173

# AI Explanation Service (Optional - Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Analysis Safety & Resource Limits
MAX_REPO_SIZE_MB=200.0
MAX_FILE_COUNT=10000
SUBPROCESS_TIMEOUT_SECONDS=180
```

---

## 8. Setup & Local Run

### Windows (PowerShell)

```powershell
# 1. Navigate to backend directory
cd backend

# 2. (Optional) Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
Copy-Item .env.example .env

# 5. Set Gemini API key (optional for local AI features)
# $env:GEMINI_API_KEY="your-key-here"

# 6. Run the FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Linux / macOS (Bash)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 9. Running Tests

Run the automated test suite inside the `backend` directory:

```bash
python -m pytest
```

All automated tests verify health probes, input validation, in-memory store operations, metrics calculation, lifecycle transitions, background orchestration, partial failure recovery, API endpoints, prompt templates, mock Gemini generation, Markdown report generation formatting, determinism, and download attachment headers.
