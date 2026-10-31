# CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring

CodeImpact is an AI-powered static code analysis and codebase intelligence platform designed to help engineering teams safely detect, prioritize, and eliminate dead code and duplication in JavaScript and TypeScript repositories.

---

## 1. Problem Statement

Modern JavaScript and TypeScript projects accumulate substantial technical debt over time:
- **Unused files, exports, and dependencies** clutter bundles and complicate refactoring.
- **Duplicated logic** introduces subtle synchronization bugs and increases maintenance overhead.
- Traditional "dead code removal" tools often produce false positives by failing to trace dynamic imports, plugin architectures, or indirect references.

CodeImpact solves this by combining **pinned static analysis engines (Knip, jscpd)** with **dependency impact analysis (Madge)** and **grounded Gemma 4 AI explanations**, ensuring that every finding is backed by verifiable static evidence without claiming code is safe to delete prematurely.

---

## 2. Architecture & Workstreams

CodeImpact is structured into four modular workstreams:

```text
┌─────────────────────────────────────────────────────────────┐
│                    BHOOMI_1: React UI                       │
│        (Vite + TypeScript + TailwindCSS + React Flow)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                  TANUJA_4: FastAPI Backend                  │
│       (Orchestration, Schemas, Stores, Gemma 4 AI)          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼───────────────┐
│     OM_2: Static Analysis   ││  SAMAR_3: Dependency Engine  │
│ • GitHub Retrieval & Sandbox││ • Madge Dependency Extraction│
│ • Knip Unused Code Scan     ││ • Circular Dependency Cycles │
│ • jscpd Duplication Groups  ││ • Impact & Risk Prioritization│
│ • Finding Normalisation     ││                              │
└─────────────────────────────┘└──────────────────────────────┘
```

---

## 3. Technology Stack

- **Integration & Backend:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn, Pytest
- **Repository Retrieval:** Git CLI (shallow clone `--depth 1`, credentials isolation)
- **Static Code Analysis:** Node.js, Knip (`5.45.0`), jscpd (`4.0.5`)
- **Dependency Graph:** Madge (`6.1.1`)
- **AI Explanations:** Gemma 4 / Gemini API
- **Frontend Dashboard:** React, TypeScript, Vite, TailwindCSS, React Flow

---

## 4. Setup & Installation

### Prerequisites
- **Git** 2.30+
- **Python** 3.11+
- **Node.js** 18+ (Node 20+ recommended) and **npm** 9+

### Step 1: Clone Repository
```bash
git clone https://github.com/DevWithOm/DeadCode-Detective.git
cd DeadCode-Detective
```

### Step 2: Install Analysis Tooling
Install pinned analysis engines inside the `tooling/` directory:
```bash
cd tooling
npm install
cd ..
```

### Step 3: Setup Backend Environment
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
cd ..
```

### Step 4: Setup Frontend Dashboard
```bash
cd frontend
npm install
cp .env.example .env
cd ..
```

---

## 5. Running the Application

### Start Backend API Server
From repository root:
```bash
# Windows PowerShell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# Linux/macOS
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health Probe: `http://localhost:8000/health`

### Start Frontend Dev Server
From repository root in a separate terminal:
```bash
cd frontend
npm run dev
```
- Frontend UI Dashboard: `http://localhost:3000`

---

## 6. API Endpoints

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness and health check | `200 OK` |
| `POST` | `/api/repositories/analyse` | Submit repository for background analysis | `202 Accepted` |
| `GET` | `/api/analyses/{id}` | Poll analysis lifecycle status & summary metrics | `200 OK` |
| `GET` | `/api/analyses/{id}/findings` | Retrieve paginated, filterable normalized findings | `200 OK` |
| `GET` | `/api/analyses/{id}/findings/{finding_id}` | Detailed finding evidence and mapped test suites | `200 OK` |
| `GET` | `/api/analyses/{id}/graph` | Directed dependency graph, hub nodes, and cycles | `200 OK` |
| `POST` | `/api/analyses/{id}/explain` | Grounded Gemini AI explanation & verification steps | `200 OK` |
| `GET` | `/api/analyses/{id}/report` | Downloadable Markdown audit report (RFC attachment) | `200 OK` |

---

## 7. Testing Instructions

Run the complete automated test suite across all four teammate modules (296 tests):
```bash
# Run from repository root
python -m pytest backend/tests/ -v

# Or run from backend directory
cd backend
python -m pytest -v
```

Test coverage includes:
- `test_e2e_integration.py`: End-to-end pipeline execution from retrieval to Markdown download.
- `test_report_generator.py` & `test_report_endpoint.py`: Deterministic Markdown audit report compilation and RFC headers.
- `test_ai_service.py`, `test_ai_prompt.py`, `test_ai_endpoint.py`: Grounded Gemini AI explanations and fallback engine.
- `test_graph_builder.py`, `test_cycle_detector.py`, `test_madge.py`: Madge dependency graph traversal and circular cycle detection.
- `test_risk_scorer.py`, `test_test_impact_analyzer.py`: Review-risk weighting and test candidate mapping.
- `test_knip.py`, `test_jscpd.py`: Knip unused code scanner and jscpd structural duplication clone grouping.
- `test_repository.py`, `test_security.py`: Safe isolated workspace containment and secret redaction.

---

## 8. Security & Hardening Boundaries

CodeImpact executes analysis against untrusted external repositories. Strict security controls are enforced:
1. **No Code Execution:** Repository code or build scripts are NEVER executed. `npm install` is NEVER run inside analyzed repositories.
2. **Subprocess Isolation:** All external commands use `shell=False`, argument lists, and execution timeouts (180s).
3. **Secret Redaction:** Subprocess output automatically masks GitHub PATs, fine-grained PATs, Bearer tokens, and embedded URL credentials before logging.
4. **Output Limits:** Subprocess stdout/stderr captures are capped at 5 MB to prevent memory exhaustion.
5. **Knip Trust Boundary:** Untrusted executable configuration files (`knip.js`, `knip.ts`) in target repositories are excluded to prevent arbitrary Node.js code execution; safe declarative configs (`knip.json`) or default entrypoints are used instead.
6. **Workspace Containment:** Workspaces are verified strictly within system temporary directories. Untrusted symbolic links are rejected.

---

## 9. Known Limitations

- **Private Repositories:** MVP supports public GitHub HTTPS repositories. Authenticated private repository support requires PAT or GitHub App configuration.
- **Dynamic References:** Static analysis cannot guarantee that an export is unreachable if it is resolved dynamically at runtime (e.g. `import(`./plugins/${name}`)`). Findings are marked as `inconclusive` evidence and require developer review.

---

## 10. License

This project is licensed under the terms of the [MIT License](LICENSE).
