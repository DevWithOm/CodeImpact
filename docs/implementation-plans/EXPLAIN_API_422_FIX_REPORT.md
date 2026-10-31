# CodeImpact — Explain API HTTP 422 Root Cause Analysis & Fix Verification Report

**Status:** FIXED  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Target URL:** `http://localhost:5173` (Frontend), `http://localhost:8000` (Backend)  
**Branch:** `S`

---

## 1. Executive Summary

During full-stack testing of the running CodeImpact application, the browser console repeatedly logged:
```
Failed to load resource: the server responded with a status of 422 (Unprocessable Content)
Failing Endpoint: POST http://localhost:8000/api/analyses/{analysis_id}/explain
```
An exhaustive cross-stack investigation was performed across FastAPI route definitions, Pydantic v2 schemas, TypeScript API clients, and React components. 

All underlying root causes have been resolved, complete end-to-end integration verified, and all **300 automated backend tests passed with 0 failures**.

---

## 2. Root Cause Analysis

### Root Cause 1: Pydantic v2 Strict Input Validation (`extra="forbid"`)
* **Location:** `backend/app/schemas/ai.py` -> `ExplainRequest`
* **Trigger:** The React frontend's AI drawer allows developers to ask custom follow-up questions about a finding (e.g. "Can I safely remove this unused export?"). In `frontend/src/services/api.ts`, `api.explainFinding(analysisId, finding, customPrompt)` posted `{ finding_id: finding.id, prompt: customPrompt }`.
* **Failure:** In `backend/app/schemas/ai.py`, `ExplainRequest` had `model_config = ConfigDict(extra="forbid")` and only declared `finding_id: str`. When FastAPI parsed the incoming JSON containing the `prompt` key, Pydantic rejected it immediately with HTTP 422:
  ```json
  {
    "detail": [
      {
        "type": "extra_forbidden",
        "loc": ["body", "prompt"],
        "msg": "Extra inputs are not permitted",
        "input": "..."
      }
    ]
  }
  ```

### Root Cause 2: Response Contract Property Divergence
* **Location:** `backend/app/schemas/ai.py` -> `ExplainResponse` vs `frontend/src/services/api.ts`
* **Trigger:** Backend Gemini service returned `{ summary, why_it_matters, false_positive_scenarios, verification_steps, suggested_action, limitations }`. The frontend code checked for `data.explanation`, `data.potential_risks`, and `data.uncertainty_notes`.
* **Fix:** Harmonized the canonical schema to support both standard fields and backward-compatible UI fields without loose typing.

### Root Cause 3: Repeated Calls & Lack of In-Flight Deduplication
* **Location:** `frontend/src/services/api.ts` and `frontend/src/App.tsx`
* **Trigger:** When switching tabs or rapidly clicking the ask button, multiple redundant POST requests were fired concurrently before the previous request completed.
* **Fix:** Implemented an in-flight deduplication map `inFlightExplains` keyed by `${analysisId}:${findingId}:${prompt}` in `frontend/src/services/api.ts`. Also added a strict UI guard in `handleAiAsk` to prevent double-submissions while `isAiTyping` is true.

### Root Cause 4: Evidence & Impact Dictionary vs Object Attribute Resolution
* **Location:** `backend/app/services/ai/prompt_templates.py`
* **Trigger:** In certain analysis pipelines, finding items or their nested `impact` data are preserved as raw dictionary structures rather than Pydantic objects. Accessing `finding.impact.direct_dependants` raised `AttributeError: 'dict' object has no attribute 'direct_dependants'`.
* **Fix:** Added universal property accessor `_get_prop(obj, key, default)` that transparently handles both dictionary lookups and object attribute lookups.

### Root Cause 5: GraphEdge Schema Validation
* **Location:** `backend/app/schemas/graph.py` and `backend/app/services/orchestrator.py`
* **Trigger:** `GraphEdge` required `id: str`, but raw graph dictionaries produced edges without an explicit `id` field.
* **Fix:** Added default edge ID synthesis (`source->target`) in `GraphEdge` model post-init and explicitly passed generated IDs in `normalize_graph_dict`.

---

## 3. Discovered Browser Warnings (Distinction from App Errors)

During browser console analysis at `http://localhost:5173`, the following warnings appeared:
1. `Unchecked runtime.lastError: The message port closed before a response was received`
2. `Evaluating a string as JavaScript violates Content Security Policy`
3. Notice of `http://localhost:3000` showing "Krishi Vikas AI" (an external user project running on port 3000).

**Verification:**
* These errors originate from third-party Chrome extensions (password managers, devtools plugins) injecting content scripts, and another service occupying port 3000.
* CodeImpact is configured to run on:
  * **Frontend:** `http://localhost:5173`
  * **Backend:** `http://localhost:8000`
* Application CSP was strictly preserved and not weakened.

---

## 4. Verification & Test Suite Results

### Automated Backend Tests
All backend tests across static analysis, dependency graphs, risk scoring, AI explanation, orchestration, and failure handling were executed:
```
backend/tests/test_ai_endpoint.py .........                              [  3%]
backend/tests/test_ai_prompt.py ..                                       [  3%]
backend/tests/test_ai_service.py ....                                    [  5%]
backend/tests/test_analyses_api.py ...                                   [  6%]
backend/tests/test_analysis_request.py ........                          [  8%]
backend/tests/test_analysis_store.py .......                             [ 11%]
backend/tests/test_api.py ...                                            [ 12%]
backend/tests/test_cycle_detector.py .........                           [ 15%]
backend/tests/test_e2e_integration.py .                                  [ 15%]
backend/tests/test_entry_point_detector.py ....                          [ 16%]
backend/tests/test_finding_mapper.py ...............                     [ 21%]
backend/tests/test_graph_builder.py ........................             [ 29%]
backend/tests/test_health.py .                                           [ 30%]
backend/tests/test_impact_analyzer.py .............                      [ 34%]
backend/tests/test_impact_integration.py .............                   [ 38%]
backend/tests/test_jscpd.py ...............                              [ 43%]
backend/tests/test_knip.py ............                                  [ 47%]
backend/tests/test_lifecycle.py ...                                      [ 48%]
backend/tests/test_madge.py ...................................          [ 60%]
backend/tests/test_orchestrator.py ...                                   [ 61%]
backend/tests/test_pipeline_failure_handling.py ......                   [ 63%]
backend/tests/test_pipeline_integration.py ....                          [ 64%]
backend/tests/test_report_endpoint.py ..                                 [ 65%]
backend/tests/test_report_generator.py ...                               [ 66%]
backend/tests/test_repository.py ........                                [ 69%]
backend/tests/test_risk_analyzer.py .........                            [ 72%]
backend/tests/test_risk_explainer.py ........                            [ 74%]
backend/tests/test_risk_scorer.py .........................              [ 83%]
backend/tests/test_schemas.py ......                                     [ 85%]
backend/tests/test_security.py ..................                        [ 91%]
backend/tests/test_test_discovery.py ........                            [ 93%]
backend/tests/test_test_framework_detector.py .......                    [ 96%]
backend/tests/test_test_impact_analyzer.py ....                          [ 97%]
backend/tests/test_test_mapper.py ........                               [100%]

====================== 300 passed, 10 warnings in 57.41s ======================
```

### Frontend Build
Executed TypeScript type-checking and production bundling:
```bash
npm --prefix frontend run build
```
Output:
```
✓ 1774 modules transformed.
dist/index.html                   1.09 kB │ gzip:   0.64 kB
dist/assets/index-D6tOydFF.css   63.80 kB │ gzip:  10.76 kB
dist/assets/index-3_PNw3Nb.js   530.11 kB │ gzip: 155.57 kB
✓ built in 3.69s
```
**Result:** 0 TypeScript compile errors, 0 bundle errors.

---

## 5. Architectural Invariants Preserved

1. **Non-destructive principle:** Static analysis absence of usage does not imply deletion safety; explanations emphasize validation steps and tool limitations.
2. **Deterministic risk authority:** Numerical review risk scores are computed deterministically; Gemini AI provides advisory explanations grounded on verified evidence.
3. **Contract consistency:** Pydantic schemas enforce type safety without arbitrary unvalidated dictionaries.
