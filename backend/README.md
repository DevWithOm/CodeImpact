# CodeImpact — FastAPI Backend

**Tagline:** "Don't Just Find Dead Code. Understand What Happens When You Remove It."  
**Role:** Person 4 — Backend Orchestration, Integration & AI.

---

## 1. Purpose

The CodeImpact backend coordinates repository analysis for JavaScript and TypeScript projects. It orchestrates:
- **Repository Retrieval & Static Analysis (Person 2 - OM_2):** Git clone, Knip, and jscpd execution.
- **Dependency Graph & Impact Analysis (Person 3 - SAMAR_3):** Madge import mapping, circular dependency detection, and risk scoring.
- **AI Explanations & Safe Recommendations (Person 4 - TANUJA_4):** Grounded Gemini explanations (Phase 4).
- **Audit Report Generation (Person 4 - TANUJA_4):** Markdown reports (Phase 5).

---

## 2. Directory Structure

```text
backend/
├── API_CONTRACT.md          # Authoritative shared API contract
├── README.md                # This setup and run guide
├── requirements.txt         # Pinned Python dependencies
├── .env.example             # Environment template
├── app/
│   ├── main.py              # FastAPI entry point, CORS, exception handlers
│   ├── core/
│   │   └── config.py        # Pydantic Settings application configuration
│   ├── api/
│   │   ├── repositories.py  # POST /api/repositories/analyse
│   │   ├── analyses.py      # GET /api/analyses/{id}, findings, finding detail, graph
│   │   ├── ai.py            # AI explanation routes (Phase 4)
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
│   │   └── orchestrator.py  # Background pipeline coordinator
│   └── utils/               # Subprocess and filesystem utilities
└── tests/
    ├── test_health.py           # Health check probe test
    ├── test_analysis_request.py # URL validation and 202 Accepted test
    ├── test_schemas.py          # Schema constraint and serialization tests
    ├── test_api.py              # Basic API route tests
    ├── test_analysis_store.py   # In-memory store operations & metrics tests
    ├── test_lifecycle.py        # Status lifecycle transitions tests
    ├── test_orchestrator.py     # Background pipeline & failure recovery tests
    └── test_analyses_api.py     # Analyses, findings, and graph API tests
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

## 4. Teammate Module Integration Status

- **Person 2 (OM_2 - Static Analysis):** Adapter interface defined in `app/adapters/static_analysis_adapter.py`. Ready to bind to `app.services.static_analysis.analyzer.analyze_repository`. If the module is pending or unpopulated, the adapter logs the pending status and tracks coverage accordingly.
- **Person 3 (SAMAR_3 - Dependency Impact):** Adapter interface defined in `app/adapters/dependency_impact_adapter.py`. Ready to bind to `app.services.dependency_impact.impact_analyzer.analyze_impact`.
- **Person 1 (BHOOMI_1 - Frontend):** All 5 core Phase 3 endpoints are live, returning typed JSON with `snake_case` properties and CORS enabled for `http://localhost:5173`.

---

## 5. Endpoints Available in Phase 3

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check probe | `200 OK` |
| `POST` | `/api/repositories/analyse` | Start analysis job in background | `202 Accepted` |
| `GET` | `/api/analyses/{analysis_id}` | Polling endpoint for job status & summary metrics | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/findings` | Paginated, filterable findings explorer | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/findings/{finding_id}` | Detailed finding evidence & test candidates | `200 OK` (or `404`) |
| `GET` | `/api/analyses/{analysis_id}/graph` | Directed dependency graph & detected cycles | `200 OK` (or `404`) |

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## 6. Setup & Local Run

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

# 5. Run the FastAPI development server
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

## 7. Running Tests

Run the automated test suite inside the `backend` directory:

```bash
python -m pytest
```

All 33 tests cover health probes, input validation, in-memory store operations, metrics calculation, lifecycle transitions, background orchestration, partial failure recovery, and API endpoints.
