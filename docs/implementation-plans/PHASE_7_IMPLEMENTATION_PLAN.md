# PHASE 7 — IMPLEMENTATION PLAN
## Service Orchestration and Team Integration

**Author:** Integration Engineer / Backend Architect  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Time Budget:** ~4 Hours  
**Status:** Approved for Execution  

---

## 1. Objectives & Scope

Connect existing, independently developed services across OM_2, SAMAR_3, and TANUJA_4 into a unified, deterministic, end-to-end analysis pipeline.

### In Scope
1. **Repository Retrieval Integration**:
   - Connect `RepositoryAdapter` to OM_2's `retrieve_repository` in `backend.app.services.repository.github_service`.
   - Ensure safe workspace isolation and cleanup.
2. **Static Analysis Integration**:
   - Connect `StaticAnalysisAdapter` to OM_2's `analyze_repository` in `backend.app.services.static_analysis.analyzer`.
3. **Dependency & Impact Engine Integration**:
   - Implement `DependencyImpactAdapter.analyze_impact` to execute SAMAR_3's multi-stage pipeline:
     1. Madge runner (`run_madge`)
     2. Graph builder (`build_dependency_graph`)
     3. Finding-level impact analyzer (`analyze_impact`)
     4. Potential test impact mapper (`analyze_test_impact`)
     5. Explainable review-risk engine (`analyze_review_risk`)
4. **Orchestrator Normalization & Resilience**:
   - Update `normalize_finding_dict` in `orchestrator.py` to extract SAMAR_3 enriched fields into `FindingItem` and `FindingImpact`.
   - Add a direct programmatic service method `run_analysis(request)` alongside `run_pipeline(analysis_id)`.
   - Update `compute_metrics` in `analysis_store.py` for cross-category compatibility (`duplicate_code` vs `duplicate_block`).
5. **Integration & Regression Testing**:
   - Verify all 285 existing tests pass.
   - Add dedicated pipeline integration and failure handling tests in `backend/tests/test_pipeline_integration.py` and `test_pipeline_failure_handling.py`.
6. **Documentation Deliverables**:
   - `PHASE_7_INTEGRATION_AUDIT.md`
   - `PHASE_7_IMPLEMENTATION_PLAN.md`
   - `PHASE_7_IMPLEMENTATION_REPORT.md`
   - `PHASE_7_INTEGRATION_CONTRACT.md`
   - `PHASE_7_REGRESSION_REPORT.md`

### Out of Scope
- Re-writing or replacing any completed Phase 1–6 module.
- Modifying frontend React source code.
- Running untrusted repository code or executing runtime tests.
- Adding heavyweight external dependencies (Redis, Celery, databases).

---

## 2. Work Breakdown & Time Allocation

| Subphase | Activity | Estimated Duration |
| :---: | :--- | :---: |
| **7A** | Repository Audit & Integration Inventory (`PHASE_7_INTEGRATION_AUDIT.md`) | 25 min |
| **7B** | Adapter Implementation & Orchestrator Hardening | 40 min |
| **7C** | Schema Normalization & Unified Contract Alignment | 30 min |
| **7D** | Pipeline Resilience & Failure Isolation | 25 min |
| **7E** | API & Frontend Contract Validation | 20 min |
| **7F** | AI & Report Integration Verification | 20 min |
| **7G** | Integration & Regression Testing (`test_pipeline_*.py`) | 45 min |
| **7H** | Security & Workspace Cleanup Validation | 15 min |
| **7I** | Documentation & Reporting (`REPORT`, `CONTRACT`, `REGRESSION`) | 20 min |
| **Total** | | **240 min (4.0 hrs)** |

---

## 3. Implementation Steps

1. **Step 1: Wire Adapters**
   - Update `RepositoryAdapter` to call `backend.app.services.repository.github_service.retrieve_repository`.
   - Update `StaticAnalysisAdapter` to call `backend.app.services.static_analysis.analyzer.analyze_repository`.
   - Update `DependencyImpactAdapter` to orchestrate `run_madge` $\rightarrow$ `build_dependency_graph` $\rightarrow$ `analyze_impact` $\rightarrow$ `analyze_test_impact` $\rightarrow$ `analyze_review_risk`.
2. **Step 2: Update Normalizers in Orchestrator & Store**
   - Update `normalize_finding_dict` in `orchestrator.py` to populate `FindingImpact` from SAMAR_3 enriched fields while preserving Phase 6 review-risk data.
   - Update `compute_metrics` in `analysis_store.py` to count duplicates and test candidates seamlessly.
   - Add programmatic `run_analysis(request: AnalysisRequest)` in `orchestrator.py`.
3. **Step 3: Verification & Test Creation**
   - Create `backend/tests/test_pipeline_integration.py` testing complete happy-path pipeline against `fixtures/sample-js-repository`.
   - Create `backend/tests/test_pipeline_failure_handling.py` testing partial failures (Madge timeout, static analysis errors, empty findings, empty graphs).
4. **Step 4: Run Complete Test Suite & Generate Final Reports**
   - Execute all tests.
   - Compile `PHASE_7_IMPLEMENTATION_REPORT.md`, `PHASE_7_INTEGRATION_CONTRACT.md`, and `PHASE_7_REGRESSION_REPORT.md`.

