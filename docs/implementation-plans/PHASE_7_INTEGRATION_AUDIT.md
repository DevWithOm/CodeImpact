# PHASE 7 — SERVICE ORCHESTRATION & TEAM INTEGRATION AUDIT
## Integration Inventory and Contract Mismatch Analysis

**Author:** Integration Engineer / Backend Architect  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Branch:** `S` (Unified Integration Workspace)  
**Status:** Audit Completed  

---

## 1. Executive Summary

Phase 7 connects the independently implemented workstreams of CodeImpact:
1. **OM_2**: Repository retrieval (`github_service.py`, `workspace.py`) and static code analysis (`knip_runner.py`, `jscpd_runner.py`, `analyzer.py`).
2. **SAMAR_3**: Dependency extraction (`madge_runner.py`), graph construction (`graph_builder.py`), cycle detection (`cycle_detector.py`), finding-level impact analysis (`impact_analyzer.py`), test discovery & mapping (`test_discovery.py`, `test_mapper.py`, `test_impact_analyzer.py`), and explainable review-risk scoring (`risk_scorer.py`, `risk_explainer.py`, `risk_analyzer.py`).
3. **TANUJA_4**: FastAPI orchestration (`orchestrator.py`), in-memory analysis store (`analysis_store.py`), Gemini AI explanations (`gemini_service.py`), and Markdown audit report generation (`report_generator.py`).
4. **BHOOMI_1**: React frontend consuming API endpoints and React Flow dependency graph visualizations.

This audit establishes the baseline status of all integration boundaries, details contract mismatches, and specifies the surgical adapter bridges required for end-to-end execution.

---

## 2. Integration Inventory

| Component | Existing File | Owner | Status | Expected Interface | Integration Status & Required Bridge |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Repository Retrieval** | `backend/app/services/repository/github_service.py` | OM_2 | Implemented & Verified | `retrieve_repository(url, branch, analysis_id) -> dict` | `RepositoryAdapter` was checking `app.services.static_analysis.analyzer` instead of `repository.github_service`. Bridge to actual implementation. |
| **Workspace Cleanup** | `backend/app/services/repository/workspace.py` | OM_2 | Implemented & Verified | `cleanup_workspace(workspace_path) -> None` | Implemented in `RepositoryAdapter.cleanup_workspace` with safe path constraints. Verified. |
| **Static Code Analysis** | `backend/app/services/static_analysis/analyzer.py` | OM_2 | Implemented & Verified | `analyze_repository(workspace_path, analysis_id) -> dict` | `StaticAnalysisAdapter` connects to `analyzer.analyze_repository`. Verified. |
| **Madge Runner** | `backend/app/services/dependency_impact/madge_runner.py` | SAMAR_3 | Implemented & Verified | `run_madge(repo_path) -> dict` | Must be called once per analysis through `DependencyImpactAdapter`. |
| **Dependency Graph** | `backend/app/services/dependency_impact/graph_builder.py` | SAMAR_3 | Implemented & Verified | `build_dependency_graph(dependency_map, cycles, findings) -> dict` | Constructs canonical directed graph. Direction: `A -> B` means `A` imports `B`. |
| **Finding Impact** | `backend/app/services/dependency_impact/impact_analyzer.py` | SAMAR_3 | Implemented & Verified | `analyze_impact(graph, findings, analysis_id) -> dict` | Enriches findings with direct dependants, dependencies, self loops, cycles. |
| **Test Impact** | `backend/app/services/dependency_impact/test_impact_analyzer.py` | SAMAR_3 | Implemented & Verified | `analyze_test_impact(graph, enriched_findings, repo_path, analysis_id) -> dict` | Maps test candidates, detected frameworks, and entry points. |
| **Review-Risk Engine** | `backend/app/services/dependency_impact/risk_analyzer.py` | SAMAR_3 | Implemented & Verified | `analyze_review_risk(graph, enriched_findings, entry_points, analysis_id) -> dict` | Computes deterministic scores (0-100), risk levels, confidence, and explanations. |
| **Dependency Impact Adapter** | `backend/app/adapters/dependency_impact_adapter.py` | TANUJA_4 / SAMAR_3 | Incomplete Stub | `analyze_impact(workspace_path, findings, analysis_id) -> dict` | **Defect**: Currently raises `IntegrationPendingError`. Must be upgraded to execute Phases 2–6 sequentially without redundant Madge calls. |
| **Pipeline Orchestrator** | `backend/app/services/orchestrator.py` | TANUJA_4 | Partially Integrated | `run_pipeline(analysis_id)` | Needs updated finding normalization to extract SAMAR_3 enriched fields into `FindingItem` and `FindingImpact`. |
| **Analysis Store** | `backend/app/services/analysis_store.py` | TANUJA_4 | Implemented & Verified | `create_analysis()`, `update_results()`, `get_findings()` | `compute_metrics` needs dual compatibility for `duplicate_code` and `duplicate_block`, plus test candidate metrics. |
| **Gemini AI Service** | `backend/app/services/ai/gemini_service.py` | TANUJA_4 | Implemented & Verified | `explain_finding(finding, repo_name, fallback_on_error) -> ExplainResponse` | Consumes `FindingItem`. Operates with deterministic fallback if API key is not configured. |
| **Report Generator** | `backend/app/services/reports/report_generator.py` | TANUJA_4 | Implemented & Verified | `generate_markdown_report(record) -> str` | Generates audit report from stored analysis records and findings. |
| **REST API Routes** | `backend/app/api/repositories.py`, `analyses.py` | TANUJA_4 | Implemented & Verified | `POST /api/repositories/analyse`, `GET /api/analyses/{id}` | Background task queues `orchestrator.run_pipeline`. Returns 202 Accepted. |

---

## 3. Contract Mismatch Analysis & Action Plan

### Mismatch 1: `RepositoryAdapter` target module import
- **Affected Modules**: `backend/app/adapters/repository_adapter.py`
- **Expected Behavior**: Calls OM_2's `retrieve_repository(repository_url, branch, analysis_id)` in `backend.app.services.repository.github_service`.
- **Actual Behavior**: Attempted to import `analyzer.retrieve_repository` from `static_analysis`, which failed and raised `IntegrationPendingError`.
- **Required Correction**: Update `RepositoryAdapter.retrieve_repository` to import and call `retrieve_repository` from `backend.app.services.repository.github_service`.

### Mismatch 2: `DependencyImpactAdapter` incomplete execution
- **Affected Modules**: `backend/app/adapters/dependency_impact_adapter.py`
- **Expected Behavior**: Single-pass execution of Madge $\rightarrow$ graph builder $\rightarrow$ Phase 4 impact analyzer $\rightarrow$ Phase 5 test mapper $\rightarrow$ Phase 6 review-risk engine.
- **Actual Behavior**: Raised `IntegrationPendingError` unconditionally.
- **Required Correction**: Implement complete pipeline in `DependencyImpactAdapter.analyze_impact` using pre-constructed graph invariants without re-running Madge or executing target repository code.

### Mismatch 3: Finding Normalization & Enriched Attribute Mapping
- **Affected Modules**: `backend/app/services/orchestrator.py` (`normalize_finding_dict`)
- **Expected Behavior**: `FindingItem` retains `impact` (with `direct_dependants`, `related_test_candidates`, `cycle_member`, `review_risk`) and preserves Phase 6 review-risk attributes (`risk_score`, `risk_confidence`, `risk_assessment`, `test_impact`).
- **Actual Behavior**: Looked only for a nested `item["impact"]` dictionary, ignoring root-level `direct_dependants`, `test_impact`, and `risk_assessment` attached by SAMAR_3.
- **Required Correction**: Update `normalize_finding_dict` to synthesize `FindingImpact` from SAMAR_3's root fields when `item.get("impact")` is absent, and populate extra fields.

### Mismatch 4: Category and Metric Alignment in Store
- **Affected Modules**: `backend/app/services/analysis_store.py` (`compute_metrics`)
- **Expected Behavior**: Correctly increments `duplicate_groups` whether the category is reported as `"duplicate_code"` (OM_2/jscpd) or `"duplicate_block"`, and counts candidate tests from both `f.impact.related_test_candidates` and `f.test_impact`.
- **Actual Behavior**: Only checked for `"duplicate_block"`.
- **Required Correction**: Broaden metric counting to support both category names.

---

## 5. Security & Isolation Invariants

1. **Zero Execution of Untrusted Target Code**: Knip, jscpd, and Madge are run via pinned Node binaries in `tooling/` with strict subprocess limits (`shell=False`, bounded timeout, bounded stdout). Target code/tests/scripts are NEVER executed.
2. **Path Sanitization**: All file paths are normalized POSIX repository-relative paths (`/`). Directory traversal (`..`) and absolute host paths are rejected.
3. **Workspace Isolation**: Each analysis allocates a unique timestamped UUID workspace inside the system temporary directory. Workspaces are cleaned up in `finally` blocks.

