# CodeImpact — Repository Scanning Failure & Connection Reset Fix Report

**Final Verdict:** FIXED  
**Date:** 2026-10-31  
**Target URLs:**  
- Frontend: `http://localhost:5173`  
- Backend: `http://localhost:8000`  
**Branch:** `S`

---

## 1. Root Cause

An exhaustive trace across the repository retrieval pipeline, backend uvicorn lifecycle, and frontend polling mechanisms revealed the exact sequence of failures:

1. **Fatal Git Clone Destination Collision (`create_workspace` vs `git clone`)**:
   `workspace.create_workspace` pre-created the subdirectory `.codeimpact/reports` inside the newly allocated workspace path (`C:\Users\...\AppData\Local\Temp\codeimpact\workspaces\{analysis_id}`) before `git clone` was called. Git shallow cloning strictly forbids non-empty target directories, causing every repository retrieval to immediately abort with:
   ```
   fatal: destination path '...' already exists and is not an empty directory.
   ```
2. **Server Reload Truncation & Connection Reset**:
   When uvicorn was running with `--reload` across the root workspace, file system change detections triggered worker process shutdowns. When the worker terminated while an HTTP status poll was in flight, the active TCP socket received `net::ERR_CONNECTION_RESET`, followed by `net::ERR_CONNECTION_REFUSED`. Because `AnalysisStore` is in-memory within that process, the restart purged active jobs, causing subsequent status polls to fail.
3. **Frontend Indefinite Polling on Error**:
   In `frontend/src/services/api.ts`, `api.getAnalysisStatus` caught network errors and silently returned `DEFAULT_SUMMARY` with an `undefined` status, which defaulted to `'running'`. The frontend therefore remained locked in a perpetual "Scanning..." state even if the backend failed or 404'd. Furthermore, `AnalysisStatusResponse.error_message` was not mapped to `data.error`, preventing error details from surfacing in the terminal logs.
4. **Repository URL Validation Shorthand**:
   The input placeholder suggested `facebook/react`, but entering shorthand names without `https://github.com/` failed Pydantic scheme validation with HTTP 422.

---

## 2. Backend Startup Findings & Status Endpoints

* **Application Entry Point:** `backend/app/main.py`
* **Health Check Probe:** `GET http://localhost:8000/health` (`{"status": "ok"}`)
* **Interactive OpenAPI Docs:** `GET http://localhost:8000/docs`
* **Analysis Submission:** `POST /api/repositories/analyse` returns HTTP `202 Accepted` with `analysis_id` (`an_xxxxxxxx`) and status `queued`.
* **Analysis Polling:** `GET /api/analyses/{analysis_id}` returns `AnalysisStatusResponse` with `status`, `stage`, `metrics`, `tool_coverage`, and `error_message`.

---

## 3. Exact Exception Recorded in Logs

From `uvicorn` worker execution log for analysis `an_a4ea3465`:
```
Repository retrieval failed for an_a4ea3465: Failed to retrieve repository 'facebook/react' on branch 'main': fatal: destination path 'C:\Users\Samar\AppData\Local\Temp\codeimpact\workspaces\an_a4ea3465' already exists and is not an empty directory.
Traceback (most recent call last):
  File "C:\DeadCode\backend\app\services\orchestrator.py", line 297, in run_pipeline
    retrieval_res = self.repo_adapter.retrieve_repository(
        repository_url=repo_url,
        branch=branch,
        analysis_id=analysis_id,
    )
  File "C:\DeadCode\backend\app\services\repository\github_service.py", line 176, in retrieve_repository
    raise RepositoryRetrievalError(...)
backend.app.services.repository.github_service.RepositoryRetrievalError: Failed to retrieve repository 'facebook/react' on branch 'main': fatal: destination path 'C:\Users\Samar\AppData\Local\Temp\codeimpact\workspaces\an_a4ea3465' already exists and is not an empty directory.
```

---

## 4. Fixes Implemented

### A. Repository Retrieval Isolation (`backend/app/services/repository/github_service.py`)
* Right after `create_workspace(analysis_id)` and immediately before invoking `git clone`, the workspace directory is verified to be completely clean/empty:
  ```python
  ws_obj = Path(workspace_path)
  for child in ws_obj.iterdir():
      if child.is_dir():
          shutil.rmtree(child, ignore_errors=True)
      else:
          child.unlink(missing_ok=True)
  ```
* After `git clone` completes successfully, `.codeimpact/reports` is synthesized inside the cloned repo.

### B. Shorthand URL Normalization (`backend/app/schemas/analysis.py` & `frontend/src/services/api.ts`)
* If a user submits `owner/repo` (e.g. `DevWithOm/DeadCode-Detective`), both backend validator and frontend client automatically normalize it to `https://github.com/owner/repo`.
* `AnalysisStatusResponse` now exposes `repository_url: str | None`.

### C. Robust Frontend Polling & Termination (`frontend/src/App.tsx` & `frontend/src/services/api.ts`)
* `api.startAnalysis` throws explicit HTTP errors instead of fabricating fake IDs.
* `api.getAnalysisStatus` handles `404 Not Found` and HTTP errors by returning terminal `status: 'failed'` and maps `data.error || data.error_message`.
* `App.tsx` tracks `consecutiveNetworkErrors` (aborts after 5 consecutive lost connections), clears intervals upon unmount or on new scan triggers, and stops the loading spinner immediately when `failed` is returned.
* Default repository updated to `https://github.com/DevWithOm/DeadCode-Detective`.

---

## 5. End-to-End Real Repository Verification

The complete analysis pipeline was executed end-to-end against a live public repository (`https://github.com/DevWithOm/DeadCode-Detective.git`, branch `main`):

```python
aid = "an_full_real_test"
req = AnalysisRequest(repository_url="https://github.com/DevWithOm/DeadCode-Detective.git", branch="main")
orchestrator.run_pipeline(aid)
```

**Results:**
* **Overall Status:** `AnalysisStatus.COMPLETED`
* **Retrieved Commit SHA:** `e30ae6f8f893282497be3a7e1aa7d709efae873f`
* **Files Analyzed:** 58 eligible TypeScript/JavaScript files
* **Findings Identified:** 19 duplicate code findings (`jscpd: completed`, 19 clone groups)
* **Dependency Graph:** 59 nodes, 1 circular dependency cycle (`madge: success`)
* **Test Impact & Review Risk:** 8 candidate test relationships mapped, all 19 findings risk-scored (`review_risk: success`)
* **Execution Time:** ~11 seconds

---

## 6. Test Suite Execution

All 300 backend tests across the full CodeImpact platform passed with 0 failures:

```
====================== 300 passed, 10 warnings in 57.74s ======================
```

Frontend production build verification (`npm run build`):
```
✓ 1774 modules transformed.
dist/index.html                   1.09 kB │ gzip:   0.64 kB
dist/assets/index-D6tOydFF.css   63.80 kB │ gzip:  10.76 kB
dist/assets/index-BOtoXPrP.js   531.14 kB │ gzip: 155.90 kB
✓ built in 3.36s
```

---

## 7. Files Modified

1. `backend/app/services/repository/github_service.py` (pre-clone clean directory guarantee)
2. `backend/app/schemas/analysis.py` (shorthand `owner/repo` support, `repository_url` in status response)
3. `backend/app/services/analysis_store.py` (`repository_url` propagated to status response)
4. `backend/tests/test_analysis_request.py` (mock background task for unit request tests)
5. `frontend/src/services/api.ts` (strict error propagation, error message mapping, shorthand normalization)
6. `frontend/src/App.tsx` (interval cleanup ref, network error limit, default repo update)

---

## 8. Final Verdict

**FIXED** — The scan button now dispatches valid requests, retrieves real repositories without directory collision, executes static analysis, dependency mapping, impact analysis, and risk scoring, and successfully updates the frontend workspace.

