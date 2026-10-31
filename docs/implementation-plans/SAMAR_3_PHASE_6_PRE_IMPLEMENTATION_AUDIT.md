# SAMAR_3 — PHASE 6 PRE-IMPLEMENTATION AUDIT
## Explainable Review-Risk Engine

**Author:** SAMAR_3 (Dependency & Impact Engine)  
**Date:** 2026-10-31  
**Repository Root:** `C:\DeadCode`  
**Target Module:** `backend/app/services/dependency_impact/`  
**Phase Status:** Phase 6 — Audit Completed  

---

## 1. Executive Summary

Phase 6 implements the **Explainable Review-Risk Engine** for CodeImpact.
Building upon the verified baselines of Phases 1 through 5, this engine assesses how carefully a human developer must inspect each static-analysis finding before making a refactoring decision.

In accordance with CodeImpact's foundational axiom:
> **"Not detected as used does not mean safe to delete."**

The Review-Risk Engine functions as an explainable decision-support system, **not** an automated deletion authorization tool. It evaluates multi-dimensional signals from static analysis findings, dependency graph topology, circular dependency structures, test impact mapping, and application entry points to produce deterministic, bounded (0–100) scores with transparent factor-level justifications and confidence ratings.

---

## 2. Existing Baseline & Signal Audit

### 2.1 Upstream Phases & Data Flow
1. **Phase 1 (Contract & Schema Foundation):**
   - Base finding schema (`Finding` in `backend/app/schemas/finding.py`).
   - Fields: `finding_id`, `category`, `file_path`, `symbol`, `source_tool`, `evidence_class`, `review_risk` (initial default `"unknown"`), `risk_factors`, `evidence`, `metadata`.
2. **Phase 2 (Madge Subprocess Runner):**
   - Subprocess execution extracting raw dependency maps and cycles with timeout, output limits, and Windows-safe handling.
3. **Phase 3 (Dependency Graph Builder & Cycle Detector):**
   - Directed graph (`GraphData`, `GraphNode`, `GraphEdge`, `GraphStats`).
   - Invariant: `A -> B` means `A` imports `B`.
   - Node in-degree = direct importers/dependants; node out-degree = direct dependencies.
   - Cycle normalization and detection distinguishing multi-file cycles from self-loops (`A -> A`).
   - Truncation indicator: `truncated: bool`.
4. **Phase 4 (Finding-Level Impact Analyzer):**
   - Enriches findings with `direct_dependants`, `direct_dependencies`, `cycle_member`, `cycles`, `self_dependency_detected`, `mapping_status`, `impact_status`, and `summary`.
5. **Phase 5 (Potential Test Impact Mapping):**
   - Enriches findings with `test_impact`: `status`, `mapping_complete`, `candidate_tests` (with `mapping_status`: `"direct"`, `"heuristic"`, `"unknown"` and `evidence_type`: `"static_import"`, `"transitive_dependency"`, `"filename_match"`, etc.), `summary` (`direct_test_count`, `heuristic_test_count`, `unknown_test_count`), and `notes`.
   - Repository-level entry points: `entry_points` (`file_path`, `entry_point_status`, `entry_point_type`, `evidence`).
   - Test frameworks: `detected_frameworks`.

### 2.2 Available Risk Signals Table

| Signal Category | Source Field | Observed Values / Types | Review Risk Significance |
| :--- | :--- | :--- | :--- |
| **Dependency Exposure** | `direct_dependants` / `summary.direct_dependant_count` | `list[DirectDependant]`, count $\ge 0$ | High dependant count indicates wide potential blast radius if modified. |
| **Direct Dependencies** | `direct_dependencies` / `summary.direct_dependency_count` | `list[DirectDependant]`, count $\ge 0$ | High out-degree indicates complex orchestration/coupling. |
| **Cycle Exposure** | `cycle_member`, `cycles`, `self_dependency_detected` | `bool`, `list[list[str]]` | Multi-file cycles amplify refactoring side-effects. Self-loops are distinguished. |
| **Entry Point Exposure** | `entry_points` (Phase 5) / path heuristic | `list[EntryPointEvidence]`, `str` | Entry points (e.g. `main`, `index`, CLI bins) lack incoming imports but run at runtime. |
| **Test Impact** | `test_impact.candidate_tests`, `test_impact.summary` | `direct`, `heuristic`, `unknown` counts | Presence of tests demands human review; absence **never** lowers risk or proves safety. |
| **Finding Properties** | `category`, `evidence_class`, `source_tool` | `unused_export`, `unused_file`, `inconclusive` | Exports risk external library breakage; inconclusive scans require heightened caution. |
| **Analysis Completeness** | `mapping_status`, `impact_status`, `truncated` | `mapped`/`unmapped`, `success`/`partial`/`unavailable` | Truncation or unavailable data limits confidence; missing data $\neq$ zero risk. |

---

## 3. Review-Risk Model Architecture

### 3.1 Review Risk Categorization
Following the Phase 1 schema, `review_risk` maps to:
- `"lower"`: Observed score 0–29 in a complete analysis with minimal blast radius.
- `"medium"`: Observed score 30–59 indicating moderate coupling or dependencies.
- `"higher"`: Observed score 60–100 indicating substantial dependants, cycles, entry points, or critical tests.
- `"unknown"`: Analysis incomplete, graph unavailable, or finding unmapped.

### 3.2 Evidence Confidence
Distinct from the risk score:
- `"high"`: Finding mapped, graph complete (`truncated == False`), test & entry point analyses complete.
- `"medium"`: Finding mapped, graph available, but secondary evidence incomplete.
- `"low"`: Graph truncated, test analysis partial, or significant structural metadata missing.
- `"unknown"`: Graph unavailable or finding unmapped.

### 3.3 Analysis Completeness
- `"complete"`: All analysis pipelines executed with full graph coverage.
- `"partial"`: Graph truncated or test impact partial.
- `"unavailable"`: Graph unavailable or finding could not be mapped.

---

## 4. Reusable Modules and Integration Points

- `backend/app/services/dependency_impact/impact_analyzer.py`:
  - `_extract_graph_info()`: Reusable for extracting graph completeness, truncation, and availability status.
  - `IMPACT_STATUS_SUCCESS`, `IMPACT_STATUS_PARTIAL`, `IMPACT_STATUS_UNAVAILABLE`.
- `backend/app/services/dependency_impact/finding_mapper.py`:
  - `MAPPING_STATUS_MAPPED`, `MAPPING_STATUS_UNMAPPED`, `MAPPING_STATUS_INVALID_PATH`, `MAPPING_STATUS_MISSING_FILE_PATH`.
- `backend/app/services/dependency_impact/entry_point_detector.py`:
  - Entry-point evidence structures and canonical matching.
- `backend/app/services/dependency_impact/test_discovery.py`:
  - Test categorization constants.

---

## 5. Scope Boundaries & Constraints

1. **Deterministic Calculation**: Absolutely no LLMs, probabilistic heuristics, or machine learning models.
2. **Strict Non-Destructive Operation**: No automatic code deletion, patching, git operations, or script execution.
3. **No Target Code Execution**: Zero execution of repository scripts, tests, or dependencies.
4. **Input Preservation**: Deep-copy all input findings; preserve all Phase 1–5 fields and unknown extra keys.
5. **No False Coverage Claims**: Never equate test candidates with runtime code coverage; never equate zero tests with safety.
6. **Owner Boundary**: SAMAR_3 exports `analyze_review_risk` from `dependency_impact/__init__.py`; TANUJA_4 integrates it into `orchestrator.py`.

