# SAMAR_3: Dependency & Impact Engine
## Phase 5: Potential Test Impact Mapping Implementation Report

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (All Acceptance Criteria Met)  

---

## A. Objective

Phase 5 introduces **Potential Test Impact Mapping** into CodeImpact's Dependency & Impact Engine.
When static code analysis (Knip/jscpd via OM_2) flags a source file (e.g. `src/services/payment.ts`) as potentially unused, duplicate, or refactoring debt, CodeImpact must discover candidate test files that could be affected if the flagged file is modified or removed.

In strict alignment with the core principle:
> *"Not detected as used does not mean safe to delete."*

The engine:
1. Distinguishes between **direct static import evidence**, **bounded transitive graph dependencies**, and **heuristic naming/directory proximity**.
2. Avoids false coverage claims (a test importing a source file indicates an import relationship, not runtime test coverage).
3. Statically detects test frameworks (Jest, Vitest, Playwright, Cypress, Mocha, Pytest) and application entry points.
4. Preserves all upstream Phase 1–4 finding fields and graph invariants.

---

## B. Existing Architecture Reused

Phase 5 builds on completed Phases 1–4 without rebuilding or duplicating components:
- **Phase 2 (`madge_runner.py`)**: Reuses safe path normalization (`normalize_repo_relative_path`), bounded streaming, and error constants.
- **Phase 3 (`graph_builder.py` & `cycle_detector.py`)**: Reuses the canonical directed graph where `source -> target` means **source imports target**, cycle detection, and truncation state.
- **Phase 4 (`impact_analyzer.py` & `finding_mapper.py`)**: Reuses $O(E)$ graph indexing (`incoming_edges` / `outgoing_edges`), finding normalization, deep copying, and finding-level direct dependant calculations.

---

## C. Implemented Modules

| Module | Status | Responsibility |
| :--- | :--- | :--- |
| `backend/app/schemas/test_impact.py` | **Created** | Pydantic v2 schemas: `TestCandidate`, `TestImpactSummary`, `FindingTestImpact`, `FrameworkEvidence`, `EntryPointEvidence`, `TestImpactAnalysisResult`. |
| `backend/app/schemas/__init__.py` | **Modified** | Re-exported Phase 5 schemas. |
| `backend/app/services/dependency_impact/test_discovery.py` | **Created** | Deterministic static test discovery and classification (`unit_test`, `integration_test`, `e2e_test`, `test_config`, `unknown_test_type`). |
| `backend/app/services/dependency_impact/test_framework_detector.py` | **Created** | Static test framework detection (Jest, Vitest, Playwright, Cypress, Mocha, Pytest) from config files and package metadata. |
| `backend/app/services/dependency_impact/entry_point_detector.py` | **Created** | Static application entry-point detection from `package.json` (`main`, `module`, `exports`, `bin`) and canonical entry filenames. |
| `backend/app/services/dependency_impact/test_mapper.py` | **Created** | Core matching logic: direct static imports, bounded transitive graph reachability (max depth: 5), and heuristic naming/directory matching. |
| `backend/app/services/dependency_impact/test_impact_analyzer.py` | **Created** | Top-level coordinator exposing `analyze_test_impact()`, preserving upstream findings, and assembling the response envelope. |
| `backend/app/services/dependency_impact/__init__.py` | **Modified** | Re-exported Phase 5 functions, detectors, and schemas. |
| `backend/tests/test_test_discovery.py` | **Created** | 8 unit tests covering test identification, classification, ignored directories, and non-test rejection. |
| `backend/tests/test_test_framework_detector.py` | **Created** | 7 unit tests covering framework detection (Jest, Vitest, Playwright, Cypress, Pytest, malformed configs). |
| `backend/tests/test_entry_point_detector.py` | **Created** | 4 unit tests covering package metadata and canonical entry points. |
| `backend/tests/test_test_mapper.py` | **Created** | 8 unit tests covering direct imports, bounded transitive reachability, cycles, and heuristics. |
| `backend/tests/test_test_impact_analyzer.py` | **Created** | 4 unit and integration tests covering end-to-end analysis, fixture verification, and Phase 4 field preservation. |

---

## D. Discovery Logic

1. **Test File Identification**:
   - Supports JavaScript, TypeScript, Python, and Java test files (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.py`, `.java`).
   - Identifies delimited suffixes: `*.test.*`, `*.spec.*`, `test_*`, `*_test.*`.
   - Identifies PascalCase test conventions: `*Test.java`, `*Test.ts`.
   - Identifies test directories: `tests/`, `test/`, `__tests__/`, `spec/`, `e2e/`, `integration/`, `unit/`.
   - Excludes helper, fixture, and mock files (e.g. `tests/fixtures/mockData.ts`, `test-utils.ts`, `setupTests.ts`) unless explicitly named as a test file.
   - Strictly ignores non-source directories: `node_modules`, `.git`, `dist`, `build`, `.venv`, `coverage`.
2. **File Classification**:
   - `e2e_test`: Paths containing `/e2e/`, `cypress/`, `playwright/`, or `.e2e.` in filename.
   - `integration_test`: Paths containing `/integration/`, `.integration.`, or `.it.` in filename.
   - `test_config`: Setup files like `setupTests.ts`, `jest.setup.js`, `*.config.*`.
   - `unit_test`: Conventional unit tests (`.test.`, `.spec.`, `__tests__/`, `tests/unit/`).
   - `unknown_test_type`: Fallback when evidence is insufficient.
3. **Framework Detection**:
   - Statically inspects `package.json` dependencies and test scripts.
   - Statically verifies configuration files (`jest.config.*`, `vitest.config.*`, `playwright.config.*`, `cypress.config.*`, `.mocharc.*`, `pytest.ini`, `pyproject.toml`).
   - Assigns deterministic confidence (`high`, `medium`, `low`).

---

## E. Mapping Logic

1. **Direct Static Import (`mapping_status: "direct"`)**:
   - For flagged source file $S$, inspect incoming edges: $T \rightarrow S$ ($T$ imports $S$).
   - If $T$ is identified as a test file, it directly imports $S$.
   - `evidence_type = "static_import"`, `dependency_path = [T, S]`.
2. **Transitive Graph Reachability (`mapping_status: "heuristic"`)**:
   - Bounded backward breadth-first search along incoming import edges starting from $S$.
   - Maximum traversal depth: `MAX_TEST_IMPACT_DEPTH = 5`.
   - Maintained `visited` set to safely navigate cyclic dependencies without infinite recursion.
   - `evidence_type = "transitive_dependency"`, `dependency_path = [T, ..., S]`.
3. **Heuristic Naming & Directory Proximity (`mapping_status: "heuristic"`)**:
   - Applied to candidate test files not connected via graph edges.
   - Extracts module stem (e.g. `src/services/payment.ts` $\rightarrow$ `payment`; `tests/payment.test.ts` $\rightarrow$ `payment`).
   - Matches:
     - Proximate/mirror directory matches (`src/components/__tests__/Button.test.tsx` vs `src/components/Button.tsx`).
     - Basename stem matches across `tests/` directories.
4. **Deduplication**:
   - Test candidates are deduplicated per finding, retaining the strongest relationship (`direct` > `transitive` > `filename_match`).

---

## F. Entry-Point Detection

- Statically inspects `package.json` for:
  - `main` $\rightarrow$ `entry_point_type: "package_main"`
  - `module` $\rightarrow$ `entry_point_type: "package_module"`
  - `bin` (string or dictionary) $\rightarrow$ `entry_point_type: "cli_bin"`
  - `exports` (string or dictionary) $\rightarrow$ `entry_point_type: "package_export"`
- Statically identifies canonical application entry files present in the repository or graph:
  - `src/index.ts`, `src/main.ts`, `src/App.tsx`, `server.ts`, `app.ts` $\rightarrow$ `entry_point_type: "application_entry"`.
- Assigns status: `"found"`, `"not_found"`, or `"unknown"`.

---

## G. Output Schema Example

```json
{
  "analysis_id": "analysis_123",
  "status": "success",
  "detected_frameworks": [
    {
      "name": "vitest",
      "confidence": "high",
      "evidence": [
        "Configuration file present: vitest.config.ts",
        "package.json dependency: vitest"
      ]
    }
  ],
  "entry_points": [
    {
      "file_path": "src/main.ts",
      "entry_point_status": "found",
      "entry_point_type": "application_entry",
      "evidence": [
        {
          "kind": "filename_convention",
          "source": "convention",
          "details": "Matches standard application entry convention: 'src/main.ts'"
        }
      ]
    }
  ],
  "enriched_findings": [
    {
      "finding_id": "f_001",
      "file_path": "src/services/payment.ts",
      "category": "unused_export",
      "direct_dependants": [...],
      "test_impact": {
        "status": "success",
        "mapping_complete": true,
        "candidate_tests": [
          {
            "file_path": "tests/payment.test.ts",
            "test_type": "unit_test",
            "mapping_status": "direct",
            "evidence_type": "static_import",
            "dependency_path": [
              "tests/payment.test.ts",
              "src/services/payment.ts"
            ],
            "reason": "Test file directly imports 'src/services/payment.ts'"
          },
          {
            "file_path": "tests/integration/payment.integration.test.ts",
            "test_type": "integration_test",
            "mapping_status": "heuristic",
            "evidence_type": "filename_match",
            "dependency_path": [],
            "reason": "Test filename stem 'payment' matches source file 'src/services/payment.ts'"
          }
        ],
        "summary": {
          "direct_test_count": 1,
          "heuristic_test_count": 1,
          "unknown_test_count": 0
        },
        "notes": [
          "Potential test relationships reflect static imports or naming conventions, not test coverage."
        ]
      }
    }
  ]
}
```

---

## H. Safety & Isolation

- **Zero Untrusted Code Execution**: All discovery, framework identification, and entry-point analysis are static file/JSON inspections. No package scripts, tests, compilers, or interpreters from analyzed repositories are run.
- **Path Sanitization**: All discovered and traversed paths pass through `normalize_repo_relative_path`. Absolute host paths, directory traversal (`..`), and hidden files are rejected.
- **Bounded Resource Consumption**:
  - Scanning ignores `node_modules`, `.git`, `dist`, `build`, `.venv`.
  - Graph traversal is bounded by `MAX_TEST_IMPACT_DEPTH = 5`.
  - Cycle detection ensures no infinite recursion occurs.

---

## I. Test Results

Executed full backend test suite via `python -m pytest backend/tests/ -v`:

| Test Suite | Total Tests | Passed | Failed | Skipped | Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `test_madge.py` (Phase 2 Runner & Windows Bounded Streaming) | 35 | 35 | 0 | 0 | 8.1s |
| `test_cycle_detector.py` (Phase 3 Cycle Extraction & Rotation) | 9 | 9 | 0 | 0 | 0.1s |
| `test_graph_builder.py` (Phase 3 Graph Construction & Integrity) | 24 | 24 | 0 | 0 | 0.4s |
| `test_finding_mapper.py` (Phase 4 Path Normalization & Mapping) | 15 | 15 | 0 | 0 | 0.2s |
| `test_impact_analyzer.py` (Phase 4 Unit Impact & Evidence) | 13 | 13 | 0 | 0 | 1.8s |
| `test_impact_integration.py` (Phase 4 Integration Hardening Tasks A–D) | 13 | 13 | 0 | 0 | 0.2s |
| **`test_test_discovery.py` (Phase 5 Discovery & Classification)** | **8** | **8** | **0** | **0** | **0.1s** |
| **`test_test_framework_detector.py` (Phase 5 Framework Detection)** | **7** | **7** | **0** | **0** | **0.1s** |
| **`test_entry_point_detector.py` (Phase 5 Entry-Point Detection)** | **4** | **4** | **0** | **0** | **0.1s** |
| **`test_test_mapper.py` (Phase 5 Direct/Transitive/Heuristic Mapping)** | **8** | **8** | **0** | **0** | **0.1s** |
| **`test_test_impact_analyzer.py` (Phase 5 Top-Level Coordinator & Fixtures)** | **4** | **4** | **0** | **0** | **0.1s** |
| **Full Backend Test Suite** | **140** | **140** | **0** | **0** | **11.3s** |

---

## J. Limitations

1. **No Assertion of Coverage**: Identifying that `tests/payment.test.ts` imports `src/services/payment.ts` proves a static import relationship, not that every function or branch in `payment.ts` is exercised by the test suite.
2. **Dynamic Imports**: Tests loaded dynamically via custom reflection or test runners without static import statements cannot be discovered via graph edges; they rely on naming heuristics.
3. **Framework-Specific Routing**: Framework conventions covered encompass standard JavaScript/TypeScript and Python tools. Highly customized internal monorepo test frameworks default to `unknown_test_type`.

---

## K. Integration Handoff for TANUJA_4

Service is exported from `backend.app.services.dependency_impact`:
```python
from backend.app.services.dependency_impact import analyze_test_impact

result = analyze_test_impact(
    graph=graph,
    enriched_findings=phase4_findings,
    repo_path=workspace_path,
    analysis_id=analysis_id,
)
```
- Ready for orchestrator inclusion between Phase 4 (Finding-Level Impact) and Phase 6 (Review-Risk Engine).
- All Phase 4 findings remain unmodified; each finding receives an attached `test_impact` dictionary.

---

## L. Final Verdict

**PASS** — All 20 Phase 5 acceptance criteria (P5-01 through P5-20) are satisfied, verified by 140 passing backend tests with 0 failures and 0 warnings.

