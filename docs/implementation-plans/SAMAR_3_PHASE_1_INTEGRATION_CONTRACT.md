# SAMAR_3: Dependency & Impact Engine
## Phase 1: Integration Contract & Repository Inspection Document

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (Phase 1 Baseline Locked)  

---

## 1. Phase Objective

The primary objective of Phase 1 is to perform an architectural and structural inspection of the existing CodeImpact codebase, examine the interfaces and expectations of collaborating team members (**BHOOMI_1**, **OM_2**, and **TANUJA_4**), and establish a locked, unambiguous integration contract before any implementation code (Madge runner, graph algorithms, test mapping, or risk assessment) is written.

---

## 2. Actual Repository Structure Inspected

A recursive filesystem inspection was conducted on repository root `C:\DeadCode`.

### 2.1 Workspace Overview
- **Repository Root:** `C:\DeadCode`
- **Backend Directory:** `C:\DeadCode\backend`
- **Frontend Directory:** `C:\DeadCode\frontend`
- **Tooling Directory:** `C:\DeadCode\tooling`
- **Fixtures Directory:** `C:\DeadCode\fixtures`
- **Documentation Directory:** `C:\DeadCode\docs`

### 2.2 Actual File Inventory and State
- **Comprehensive Documentation Exists:**
  - `docs/PRD.md` (Product Requirements Document v1.2)
  - `docs/TRD.md` (Technical Requirements Document v1.2)
  - `docs/DESIGN.md` (System Design Document v1.0)
  - `docs/APP_FLOW.md` (Application Flow v1.0)
  - `docs/implementation-plans/BHOOMI_1.md` (Frontend & UI/UX Plan)
  - `docs/implementation-plans/OM_2.md` (Static Code Analysis Plan)
  - `docs/implementation-plans/SAMAR_3.md` (Dependency & Impact Engine Plan)
  - `docs/implementation-plans/TANUJA_4.md` (AI Assistant & Backend Integration Plan)
- **Scaffolded Codebase:**
  All existing `.py`, `.ts`, and `.json` files in `backend/`, `frontend/`, `tooling/`, and `fixtures/` were committed in `6bec358` as 0-byte structural placeholders.
  - No existing Pydantic classes or Python functions are currently defined or executing in `backend/`.
  - The repository layout establishes clear modular boundaries ready for implementation.

---

## 3. Existing Backend Architecture

The backend follows a standard modular FastAPI architecture under `backend/app/`:

```text
backend/
├── requirements.txt                  # Python dependencies (to be populated)
├── .env.example
├── app/
│   ├── main.py                       # FastAPI application entry point
│   ├── core/
│   │   ├── config.py                 # App settings & environment variables
│   │   └── logging.py                # Structured logging configuration
│   ├── api/                          # FastAPI route handlers
│   │   ├── analyses.py               # Analysis start & status endpoints
│   │   ├── findings.py               # Findings list & detail endpoints
│   │   ├── graph.py                  # Graph retrieval endpoints
│   │   ├── ai.py                     # AI explanation endpoints
│   │   ├── reports.py                # Report generation endpoints
│   │   └── repositories.py           # Repository submission endpoints
│   ├── schemas/                      # Pydantic v2 data models
│   │   ├── analysis.py
│   │   ├── finding.py
│   │   ├── graph.py
│   │   ├── evidence.py
│   │   └── ai.py
│   ├── services/                     # Business logic services
│   │   ├── orchestrator.py           # End-to-end analysis orchestration (TANUJA_4)
│   │   ├── repository/               # Clone & workspace management (OM_2/TANUJA_4)
│   │   ├── static_analysis/          # Knip & jscpd static tools (OM_2)
│   │   ├── dependency_impact/        # Dependency graph, cycles, risk (SAMAR_3)
│   │   ├── ai/                       # Gemma AI integration (TANUJA_4)
│   │   └── reports/                  # Markdown report generator (TANUJA_4)
│   └── utils/
│       ├── subprocess_runner.py      # Safe subprocess execution wrapper
│       └── file_utils.py             # Path & file helpers
└── tests/                            # Pytest test suite
    ├── test_api.py
    ├── test_knip.py
    ├── test_jscpd.py
    ├── test_madge.py
    ├── test_risk_engine.py
    └── test_repository.py
```

---

## 4. Existing Finding Schema (from OM_2)

Based on inspection of `docs/implementation-plans/OM_2.md` and `docs/TRD.md`, OM_2 produces normalized findings with the following structure:

```json
{
  "finding_id": "f_001",
  "category": "unused_export",
  "title": "Potentially unused export",
  "file_path": "src/utils/helpers.ts",
  "start_line": 12,
  "end_line": 18,
  "symbol": "formatDate",
  "source_tool": "knip",
  "description": "No static reference was found by the configured scan.",
  "evidence_class": "inconclusive",
  "review_risk": "unknown",
  "evidence": [
    {
      "kind": "static_reference_scan",
      "status": "not_found",
      "source": "knip",
      "details": "No direct static reference was returned by this configured scan."
    }
  ],
  "risk_factors": [],
  "metadata": {}
}
```

### Verified Field Rules:
- `finding_id`: Unique stable identifier per finding within an analysis.
- `file_path`: Repository-relative POSIX path (e.g., `src/utils/helpers.ts`).
- `category`: Standard category enum (`unused_file`, `unused_export`, `unused_dependency`, `duplicate_code`, etc.).
- `review_risk`: Initialized as `"unknown"` by OM_2; to be evaluated and updated by SAMAR_3.
- `start_line` / `end_line`: Integer line numbers or `null` if the finding applies to the whole file.

---

## 5. Existing Pydantic Schemas

While the physical files in `backend/app/schemas/` are currently 0-byte placeholders awaiting Phase 2 development, their specifications in `docs/TRD.md` and teammate implementation plans dictate Pydantic v2 models for:
- `Finding` & `EvidenceItem` (`schemas/finding.py`, `schemas/evidence.py`)
- `GraphData`, `GraphNode`, `GraphEdge`, `GraphStats` (`schemas/graph.py`)
- `AnalysisSummary`, `AnalysisStatus` (`schemas/analysis.py`)

SAMAR_3 will define and export compatible Pydantic schemas in `backend/app/schemas/graph.py` (and relevant impact schemas) without conflicting with existing models.

---

## 6. Required Input Contract

The dependency-impact module exposes a pure Python service interface callable by `orchestrator.py` (TANUJA_4):

```python
def analyze_impact(
    repo_path: str,
    findings: list[dict],
    analysis_id: str,
) -> dict:
    """Analyze dependencies and calculate impact for findings.
    
    Args:
        repo_path: Absolute local path to the already-cloned repository root.
        findings: List of normalized static analysis findings from OM_2.
        analysis_id: Unique identifier for the analysis execution.
        
    Returns:
        Dictionary conforming to the Graph Response and Enriched Findings contract.
    """
```

### Constraints on Inputs:
1. `repo_path`: Must be an absolute path to an existing, isolated workspace directory. The module **must not** perform any `git clone` or external network fetch.
2. `findings`: Must be accepted as provided without mutating or deleting OM_2's original fields.
3. `analysis_id`: Must be passed through and included in the output dictionary.

---

## 7. Required Graph Response Contract

The returned dictionary from `analyze_impact()` must contain the `graph` payload consumed by TANUJA_4's API and rendered by BHOOMI_1's React Flow component:

```json
{
  "analysis_id": "analysis_123",
  "graph": {
    "nodes": [
      {
        "id": "src/main.ts",
        "label": "main.ts",
        "file_path": "src/main.ts",
        "finding_count": 1,
        "cycle_member": false,
        "in_degree": 0,
        "out_degree": 1
      }
    ],
    "edges": [
      {
        "id": "src/main.ts->src/app.ts",
        "source": "src/main.ts",
        "target": "src/app.ts",
        "relationship": "imports"
      }
    ],
    "cycles": [
      ["src/services/auth.ts", "src/services/user.ts"]
    ],
    "stats": {
      "node_count": 2,
      "edge_count": 1,
      "cycle_count": 0,
      "original_node_count": 2,
      "original_edge_count": 1,
      "returned_node_count": 2,
      "returned_edge_count": 1
    },
    "truncated": false
  },
  "enriched_findings": []
}
```

---

## 8. Required Enriched Finding Contract

Each finding associated with a file path will be enriched with an `impact` object:

```json
{
  "finding_id": "f_001",
  "impact": {
    "direct_dependants": [
      "src/app.ts"
    ],
    "direct_dependencies": [
      "src/utils.ts"
    ],
    "dependency_count": 1,
    "dependant_count": 1,
    "cycle_member": false,
    "entry_point_evidence": "not_found",
    "related_test_candidates": [
      {
        "file_path": "tests/app.test.ts",
        "reason": "Test file directly imports the source module",
        "mapping_strength": "direct"
      }
    ],
    "risk_factors": [
      "direct_dependants:1"
    ],
    "review_risk": "medium"
  }
}
```

### Enumerations & Permitted Values:
- **`review_risk`**: `"lower"` | `"medium"` | `"higher"` | `"unknown"`
- **`mapping_strength`**: `"direct"` | `"heuristic"` | `"unknown"`
- **`entry_point_evidence`**: `"found"` | `"not_found"` | `"unknown"` | `"not_checked"`

---

## 9. Edge-Direction Convention (CRITICAL RULE)

```text
SOURCE IMPORTS TARGET (source -> target)
```

Example:
- Edge: `src/main.ts -> src/app.ts`
- Meaning: `src/main.ts` imports `src/app.ts`.
- `in_degree` of `src/app.ts`: Number of modules importing `app.ts` (its dependants).
- `out_degree` of `src/main.ts`: Number of modules imported by `main.ts` (its dependencies).

**Notice:** BHOOMI_1's React Flow layout depends strictly on this direction. Reversing this convention would display reverse architecture flows and break graph rendering.

---

## 10. Repository Path Convention

1. **POSIX Separators (`/`):** All paths in nodes, edges, cycles, findings, and test candidates must strictly use forward slashes (`/`), even when executed on Windows hosts.
2. **Repository-Relative Paths:** Paths must always be relative to the target repository root (e.g., `src/index.ts`, `tests/unit/app.test.ts`).
3. **No Absolute Path Leaks:** Absolute host paths (such as `C:\DeadCode\...` or `/tmp/codeimpact/...`) must never be present in graph node IDs, edge endpoints, finding paths, or API responses.
4. **Stable Identifiers:** A node's `id` is identical to its normalized repository-relative `file_path`.

---

## 11. Agreed Function Signature

The central entry point for the SAMAR_3 module is:

```python
# In backend/app/services/dependency_impact/impact_analyzer.py:

def analyze_impact(
    repo_path: str,
    findings: list[dict],
    analysis_id: str,
) -> dict:
    ...
```

This function will also be exposed directly from the package `backend.app.services.dependency_impact`:
```python
from backend.app.services.dependency_impact import analyze_impact
```

---

## 12. Planned Module Structure

The existing package structure in `backend/app/services/dependency_impact/` will be used to house the implementation cleanly:

```text
backend/app/services/dependency_impact/
├── __init__.py               # Re-exports analyze_impact and main dataclasses/schemas
├── madge_runner.py           # Subprocess wrapper for Madge CLI
├── graph_builder.py          # Node, edge, degree, and graph statistics builder
├── cycle_detector.py         # Cycle extraction and node cycle-membership mapping
├── test_mapper.py            # Test file detection & relation heuristics
├── risk_engine.py            # Deterministic, explainable review-risk calculator
└── impact_analyzer.py        # Main service coordinator (implements analyze_impact)
```

Matching test files in `backend/tests/`:
```text
backend/tests/
├── test_madge.py             # Madge runner and JSON parsing tests
├── test_risk_engine.py       # Review-risk rule validation tests
└── fixtures/
    └── dependency_fixture/   # Fixed JS/TS fixture repository for integration testing
```

---

## 13. Component Responsibilities

1. **`madge_runner.py`:**
   - Spawns Madge CLI safely against the workspace.
   - Extracts module dependency maps (`--json`) and circular dependencies (`--circular --json`).
   - Handles subprocess timeouts, exit codes, and errors gracefully.
   - Never alters workspace files or runs repository scripts.

2. **`graph_builder.py`:**
   - Converts raw dependency maps into structured `nodes` and `edges`.
   - Computes node metrics: `in_degree`, `out_degree`.
   - Populates `finding_count` per node from input findings.
   - Computes graph summary stats (`node_count`, `edge_count`, `cycle_count`).
   - Implements bounded graph truncation (`truncated: true/false`, with original vs returned counts).

3. **`cycle_detector.py`:**
   - Normalizes circular dependency chains into lists of file paths.
   - Flags individual nodes as `cycle_member: true/false`.

4. **`test_mapper.py`:**
   - Discovers test files in the workspace (`*.test.*`, `*.spec.*`, `__tests__/**`).
   - Maps source files to potentially related tests using:
     - Direct import inspection (strength: `direct`).
     - Basename/path pattern matching (strength: `heuristic`).
   - Labels evidence transparently; never claims full coverage.

5. **`risk_engine.py`:**
   - Evaluates deterministic, explainable rules based on direct dependants, cycles, entry points, and test evidence.
   - Generates explicit `risk_factors` strings (e.g., `"direct_dependants:3"`, `"cycle_member"`).
   - Produces risk label (`lower`, `medium`, `higher`, `unknown`).
   - Keeps risk as `unknown` when essential evidence is missing.

6. **`impact_analyzer.py`:**
   - Coordinates the pipeline: Madge execution -> Graph building -> Cycle tagging -> Test mapping -> Risk calculation -> Finding enrichment.
   - Returns the complete contract dictionary.

---

## 14. Integration Dependencies with OM_2

- **Workspace Path:** OM_2 creates/retrieves the workspace (via `retrieve_repository`). TANUJA_4's orchestrator passes this same `workspace_path` to SAMAR_3. OM_2 must not clean up the directory before SAMAR_3 runs.
- **Findings Input:** OM_2 produces findings with `finding_id` and `file_path`. SAMAR_3 reads these without renaming fields and returns finding-level impact data correlated by `finding_id`.
- **Tool Independence:** If static analysis tools (Knip/jscpd) fail or report 0 findings, SAMAR_3 can still construct the full dependency graph and cycle report.

---

## 15. Integration Dependencies with TANUJA_4

- **Orchestration:** `backend/app/services/orchestrator.py` imports `analyze_impact` from `backend.app.services.dependency_impact`.
- **Async Safety:** `analyze_impact` will run synchronously or in a thread pool via FastAPI's background tasks without blocking the main event loop.
- **Error Handling:** If Madge is missing or encounters a parsing error, `analyze_impact` returns structured fallback data with appropriate warning/stats flags, never throwing unhandled 500 exceptions into the orchestrator.

---

## 16. Frontend Graph Requirements for BHOOMI_1

- **React Flow Schema:**
  - Nodes: `{ id, label, file_path, finding_count, cycle_member, in_degree, out_degree }`
  - Edges: `{ id, source, target, relationship: "imports" }`
  - Cycles: Array of cycle path arrays (e.g., `[["src/a.ts", "src/b.ts"]]`).
- **Graph Limits:** If graph exceeds reasonable rendering limits (e.g., > 150 nodes/edges in MVP), truncation flags and counts are explicitly provided.
- **Predictable Coordinates:** Frontend handles layout algorithms (e.g., Dagre or ELK); backend provides the clean topological graph model.

---

## 17. Safety & Engineering Constraints

1. **Target Repository Isolation:**
   - NEVER execute code from the analyzed repository.
   - NEVER invoke `npm install`, `yarn install`, or package scripts in the target repository.
   - NEVER write, modify, or delete files in the analyzed repository.
2. **Subprocess Isolation:**
   - Subprocess execution must always pass argument lists (`shell=False`).
   - Fixed timeout (e.g., 30–60s) on all external tool calls.
   - Strict capture and limits on `stdout` and `stderr` buffers.
3. **Data Integrity:**
   - No absolute paths leaked in JSON responses.
   - Missing edges signify "not observed by configured static scan", never "guaranteed unreferenced".
   - Review risk represents review prioritization, not safe-to-delete certainty.

---

## 18. Identified Conflicts & Resolutions

| Topic | Discovered Variant | Resolved Contract Standard | Status |
| :--- | :--- | :--- | :--- |
| **Edge Direction** | In informal discussion, some graph tools represent `target` as the importer. | **Locked:** `source` imports `target` (`source -> target`). Required by BHOOMI_1 React Flow. | **VERIFIED & LOCKED** |
| **Service Location** | Prompt suggested `backend/app/analyzers/` vs repo having `backend/app/services/dependency_impact/`. | **Resolved:** Follow existing repository structure in `backend/app/services/dependency_impact/`. | **VERIFIED & LOCKED** |
| **Graph Edge Field** | TRD 10.2 mentioned `"type": "import"`; Plan mentioned `"relationship": "imports"`. | **Resolved:** Use `"relationship": "imports"` (with optional `"type": "import"` alias for backwards compatibility). | **VERIFIED & RESOLVED** |
| **Review Risk Values** | Some early docs mentioned numeric risk scores. | **Resolved:** Strict categorical values: `"lower"`, `"medium"`, `"higher"`, `"unknown"`. No pseudo-percentages. | **VERIFIED & LOCKED** |
| **Workspace Cleanup** | Potential race condition if OM_2 deletes workspace early. | **Resolved:** Orchestrator (TANUJA_4) owns lifecycle cleanup after all services complete. | **VERIFIED & LOCKED** |

---

## 19. Pending Decisions Requiring Team Confirmation

1. **Node.js Environment / Madge CLI Availability:**
   - *Current assumption:* Node.js and Madge are installed globally or in `tooling/package.json` (`npx madge`).
   - *Status:* **PENDING CONFIRMATION** in Phase 2 environment pre-flight check.
2. **Combined Findings Endpoint Response:**
   - *Current assumption:* TANUJA_4's orchestrator merges SAMAR_3's `enriched_findings` with OM_2's findings list under each finding's `"impact"` key.
   - *Status:* **PENDING CONFIRMATION** with TANUJA_4 during API schema finalization.

---

## 20. Phase 1 Completion Checklist

- [x] Existing repository structure was inspected.
- [x] Existing backend entry point was identified (`backend/app/main.py`).
- [x] Existing finding schema was located and documented.
- [x] Existing Pydantic model plans were identified.
- [x] Repository workspace convention was identified.
- [x] Function signature `analyze_impact(repo_path, findings, analysis_id)` was documented.
- [x] Graph response contract was documented.
- [x] Enriched finding contract was documented.
- [x] Edge direction is explicitly `source imports target`.
- [x] Path convention (POSIX, repo-relative, no absolute leaks) is documented.
- [x] Planned module responsibilities are documented.
- [x] Safety constraints are recorded.
- [x] Integration conflicts are identified and resolved.
- [x] Phase 1 documentation was created (`docs/implementation-plans/SAMAR_3_PHASE_1_INTEGRATION_CONTRACT.md`).
- [x] No unrelated modules were modified.
- [x] No implementation from later phases was started.

