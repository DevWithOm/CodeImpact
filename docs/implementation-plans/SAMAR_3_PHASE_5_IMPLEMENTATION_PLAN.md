# SAMAR_3: Dependency & Impact Engine
## Phase 5: Potential Test Impact Mapping Implementation Plan

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** READY FOR IMPLEMENTATION  

---

## 1. Objective & Scope

Phase 5 equips CodeImpact with the ability to identify potential test files related to static analysis findings, detect testing frameworks, and discover application entry points.

### In Scope:
1. Deterministic test file discovery and classification (`unit_test`, `integration_test`, `e2e_test`, `test_config`, `unknown_test_type`).
2. Direct static test impact mapping via dependency graph edges (`mapping_status: "direct"`).
3. Heuristic test impact mapping via basename matching, suffix matching, and directory proximity (`mapping_status: "heuristic"`).
4. Transitive test reachability mapping bounded by `MAX_TEST_IMPACT_DEPTH = 5` and cycle-safe (`mapping_status: "heuristic"`).
5. Static test framework detection (Jest, Vitest, Mocha, Playwright, Cypress, Pytest).
6. Static application entry-point detection (`package.json`, standard entry filenames).
7. Transparent evidence model and non-coverage terminology.
8. Pydantic v2 schemas and public service interface `analyze_test_impact`.

### Out of Scope:
- Runtime test execution or coverage measurements.
- Risk scoring (Phase 6).
- AI explanation generation.
- Code deletion or automatic test modifications.

---

## 2. Component Design & Responsibilities

### 2.1 `backend/app/schemas/test_impact.py`
- `TestCandidate`:
  - `file_path`: str
  - `test_type`: str (`unit_test`, `integration_test`, `e2e_test`, `test_config`, `unknown_test_type`)
  - `mapping_status`: str (`direct`, `heuristic`, `unknown`)
  - `evidence_type`: str (`static_import`, `transitive_dependency`, `filename_match`, `directory_match`)
  - `dependency_path`: list[str] (e.g. `["tests/app.test.ts", "src/app.ts"]`)
  - `reason`: str
- `TestImpactSummary`:
  - `direct_test_count`: int
  - `heuristic_test_count`: int
  - `unknown_test_count`: int
- `FindingTestImpact`:
  - `status`: str (`success`, `partial`, `unavailable`)
  - `mapping_complete`: bool
  - `candidate_tests`: list[TestCandidate]
  - `summary`: TestImpactSummary
  - `notes`: list[str]
- `FrameworkEvidence`:
  - `name`: str
  - `confidence`: str (`high`, `medium`, `low`)
  - `evidence`: list[str]
- `EntryPointEvidence`:
  - `file_path`: str
  - `entry_point_status`: str (`found`, `not_found`, `unknown`, `not_checked`)
  - `entry_point_type`: str (`application_entry`, `package_main`, `script_entry`, `cli_bin`)
  - `evidence`: list[dict[str, Any]]
- `TestImpactAnalysisResult`:
  - `analysis_id`: str
  - `status`: str
  - `detected_frameworks`: list[FrameworkEvidence]
  - `entry_points`: list[EntryPointEvidence]
  - `enriched_findings`: list[dict[str, Any]]

### 2.2 `test_discovery.py`
- Identify test files by regex/glob patterns (`*.test.*`, `*.spec.*`, `__tests__/**`, `tests/**`, `test/**`).
- Classify:
  - `e2e_test`: path contains `/e2e/`, `*.e2e.test.*`, `cypress/`, `playwright/`
  - `integration_test`: path contains `/integration/`, `*.integration.test.*`
  - `test_config`: `*.config.*`, `setupTests.*`
  - `unit_test`: standard `*.test.*`, `*.spec.*`
  - `unknown_test_type`: default fallback

### 2.3 `test_framework_detector.py`
- Statically check `package.json` (`devDependencies`, `dependencies`, `scripts`).
- Statically check for config files: `jest.config.*`, `vitest.config.*`, `.mocharc.*`, `playwright.config.*`, `cypress.config.*`, `pytest.ini`.

### 2.4 `entry_point_detector.py`
- Statically check `package.json` (`main`, `module`, `exports`, `bin`, `scripts`).
- Check repository files for canonical entry points (`src/index.*`, `src/main.*`, `src/App.*`, `server.ts`, `app.ts`).

### 2.5 `test_mapper.py`
- Build incoming and outgoing adjacency maps.
- **Direct**: Find test nodes in graph where `edge: test -> source`.
- **Transitive**: Breadth-first search from candidate test files backward to source, bounded by depth 5, tracking path and visited set.
- **Heuristic**:
  - Exact basename stem match (`payment.ts` vs `tests/payment.test.ts`).
  - Suffix match (`auth.ts` vs `src/auth.spec.ts`).
  - Directory proximity (`src/components/__tests__/Button.test.tsx` vs `src/components/Button.tsx`).
- Deduplicate candidates, keeping the highest confidence relationship (`direct` > `heuristic`).

### 2.6 `test_impact_analyzer.py`
- Orchestrates:
  1. Discovery of all test files (from graph nodes + repository file walk if available).
  2. Framework detection.
  3. Entry-point detection.
  4. For each finding in `enriched_findings`:
     - Run `test_mapper` against the finding's `file_path`.
     - Attach `test_impact` payload to finding.
  5. Assemble top-level response envelope.

---

## 3. Step-by-Step Execution Plan

1. **Subphase 5.1**: Create Pydantic v2 schemas in `backend/app/schemas/test_impact.py`.
2. **Subphase 5.2**: Implement `backend/app/services/dependency_impact/test_discovery.py`.
3. **Subphase 5.3**: Implement `backend/app/services/dependency_impact/test_framework_detector.py`.
4. **Subphase 5.4**: Implement `backend/app/services/dependency_impact/entry_point_detector.py`.
5. **Subphase 5.5**: Implement `backend/app/services/dependency_impact/test_mapper.py`.
6. **Subphase 5.6**: Implement `backend/app/services/dependency_impact/test_impact_analyzer.py` and update `__init__.py`.
7. **Subphase 5.7**: Author comprehensive unit & integration tests (`test_test_discovery.py`, `test_test_mapper.py`, `test_test_framework_detector.py`, `test_entry_point_detector.py`, `test_test_impact_analyzer.py`).
8. **Subphase 5.8**: Execute full regression suite and document outcomes.

