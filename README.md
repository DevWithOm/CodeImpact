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

### Step 4: Setup Frontend (When Available)
```bash
cd frontend
npm install
cd ..
```

---

## 5. Running the Application

### Start Backend API Server
From repository root:
```bash
# With venv activated
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be accessible at: `http://localhost:8000/docs`

### Start Frontend Dev Server
From repository root:
```bash
cd frontend
npm run dev
```
Frontend will be accessible at: `http://localhost:5173`

---

## 6. API Usage Example

### Start an Analysis
```bash
curl -X POST "http://localhost:8000/api/repositories/analyse" \
     -H "Content-Type: application/json" \
     -d '{"repository_url": "https://github.com/facebook/react", "branch": "main"}'
```
Response (`202 Accepted`):
```json
{
  "analysis_id": "an_a1b2c3d4e5f6",
  "status": "queued",
  "repository": "facebook/react",
  "branch": "main"
}
```

### Poll Analysis Status & Metrics
```bash
curl "http://localhost:8000/api/analyses/an_a1b2c3d4e5f6"
```

### Retrieve Normalized Findings
```bash
curl "http://localhost:8000/api/analyses/an_a1b2c3d4e5f6/findings?category=duplicate_code"
```

### Request Grounded AI Explanation
```bash
curl -X POST "http://localhost:8000/api/analyses/an_a1b2c3d4e5f6/explain" \
     -H "Content-Type: application/json" \
     -d '{"finding_id": "f_dup_001"}'
```

---

## 7. Testing Instructions

### Run Static Analysis & Security Test Suite
From the repository root:
```bash
python -m pytest backend/tests/ -v
```

Test suites include:
- `test_repository.py`: Workspace lifecycle, URL validation, size caps, and branch sanitization.
- `test_knip.py`: Knip 5.45.0 execution, version detection, unused file/export/dependency detection.
- `test_jscpd.py`: jscpd 4.0.5 execution, clone detection, multi-location duplicate grouping.
- `test_security.py`: Secret redaction, output truncation, symlink rejection, and untrusted config protection.

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
