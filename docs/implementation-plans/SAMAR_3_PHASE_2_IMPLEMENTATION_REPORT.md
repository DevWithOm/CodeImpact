# SAMAR_3: Dependency & Impact Engine
## Phase 2: Madge Subprocess Runner & Environment Integration Report

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (All 15 Unit & Real Integration Tests Passing)  
**Time Allocation:** ~35 minutes  
**Target Module:** `backend/app/services/dependency_impact/madge_runner.py`  

---

## 1. Phase Objective

Implement a production-grade, secure, and isolated Python subprocess integration with Madge to extract module dependency maps, circular dependency chains, and diagnostic telemetry from JavaScript and TypeScript repository workspaces without executing target repository code or mutating source files.

---

## 2. Environment Verification

Host environment verification:
- **Operating System:** Windows (win32)
- **Node.js Version:** `v24.14.0`
- **npm Version:** `11.9.0`
- **Python Version:** `Python 3.14.3`
- **Pytest Version:** `pytest 9.1.1`

---

## 3. Madge Version & Installation Details

- **Madge Pinned Version:** `8.0.0` (exact save)
- **Installation Location:** `tooling/` (isolated from target repository and application runtime)
- **Installation Command:**
  ```powershell
  npm --prefix tooling install --save-exact madge@8.0.0
  ```
- **Generated Artifacts:**
  - `tooling/package.json` (pinned `"madge": "8.0.0"`)
  - `tooling/package-lock.json`
  - `tooling/node_modules/` (git-ignored)
- **Executable Verified:**
  - Windows: `tooling/node_modules/.bin/madge.cmd`
  - POSIX: `tooling/node_modules/.bin/madge`

---

## 4. Executable Discovery Strategy

Implemented in `find_madge_executable()`:
1. **Priority 1 (Project-Local Tooling):** Traverses parent directory hierarchy from `__file__` to find `tooling/node_modules/.bin/madge.cmd` (or `madge` on Linux/macOS).
2. **Priority 2 (Global PATH):** Uses `shutil.which("madge.cmd")` and `shutil.which("madge")`.
3. **Fallback:** Returns `None`, signaling the caller to emit canonical `status: "unavailable"` and error `MADGE_NOT_FOUND`.

---

## 5. Implemented File Structure

```text
backend/
├── app/
│   └── services/
│       └── dependency_impact/
│           ├── __init__.py           # Re-exports run_madge, error codes, and statuses
│           └── madge_runner.py       # Complete Madge subprocess execution engine
└── tests/
    ├── test_madge.py                 # 15 unit and integration tests (100% passing)
    └── fixtures/
        └── dependency_fixture/       # Controlled TS/JS dependency fixture
            ├── src/
            │   ├── main.ts           # Imports app.ts
            │   ├── app.ts            # Imports utils.ts
            │   ├── utils.ts          # Leaf module (zero imports)
            │   └── services/
            │       ├── auth.ts       # Circular import with user.ts
            │       └── user.ts       # Circular import with auth.ts
            └── tests/
                └── app.test.ts       # Imports src/app.ts

tooling/
├── package.json                      # Pinned madge 8.0.0
└── package-lock.json
```

---

## 6. Runner Architecture

The runner provides three public interfaces and one coordinator:
- `get_dependency_map(repo_path, timeout_seconds=30)`: Extracts file-level dependency mapping (`dict[str, list[str]]`).
- `get_circular_dependencies(repo_path, timeout_seconds=30)`: Extracts circular dependency chains (`list[list[str]]`).
- `run_madge(repo_path, timeout_seconds=30)`: Orchestrates dependency and cycle extraction into the unified canonical result dictionary.
- `get_madge_version()`: Retrieves installed version metadata.

---

## 7. Subprocess Safety Controls

1. **Argument Lists & `shell=False`:** Subprocess calls always pass structured argument lists with `shell=False`, preventing shell injection vulnerabilities.
2. **Explicit Working Directory (`cwd`):** Set directly to the validated repository workspace path.
3. **Execution Deadlines:** Enforces a configurable timeout (default: 30s) catching `subprocess.TimeoutExpired`.
4. **Bounded Buffers:** Maximum output capture capped at 5MB (`MAX_OUTPUT_BYTES`) to prevent memory exhaustion on giant repositories.
5. **Path Validation:** Confirms target path exists, is non-empty, and is a directory before spawning any process.
6. **Error Sanitization:** Strips host absolute path roots (e.g. `C:\DeadCode\...` or `/home/...`), replacing them with `<repo_root>` or `<path>` to prevent machine path leakage in public APIs.

---

## 8. Dependency Map Parsing & Canonical Format

Executed using:
```powershell
madge --extensions ts,tsx,js,jsx --json .
```

### Actual Fixture Output
```json
{
  "src/app.ts": [
    "src/utils.ts"
  ],
  "src/main.ts": [
    "src/app.ts"
  ],
  "src/services/auth.ts": [
    "src/services/user.ts"
  ],
  "src/services/user.ts": [
    "src/services/auth.ts"
  ],
  "src/utils.ts": [],
  "tests/app.test.ts": [
    "src/app.ts"
  ]
}
```

- Direction: `source` imports `target` (`src/main.ts -> src/app.ts`).
- Leaf nodes (such as `src/utils.ts`) explicitly retain empty lists (`[]`).

---

## 9. Circular Dependency Extraction

Executed using:
```powershell
madge --extensions ts,tsx,js,jsx --circular --json .
```

### Critical Madge 8.0.0 Behavior Handled
In Madge CLI, exit code `1` is emitted when circular dependencies are detected (designed for CI gate checks). The runner handles this by verifying JSON validity:
- Exit code 0 + JSON array: Valid (zero cycles detected).
- Exit code 1 + JSON array: Valid (cycles detected).
- Exit code != 0 + Non-JSON / stderr: Handled as true execution failure.

### Actual Fixture Output
```json
[
  [
    "src/services/auth.ts",
    "src/services/user.ts"
  ]
]
```

---

## 10. Path Normalization Rules

Implemented in `normalize_repo_relative_path()`:
- Converts Windows backslashes (`\`) to POSIX forward slashes (`/`).
- Strips leading `./`.
- Rejects paths containing path traversal (`..`).
- Rejects absolute machine paths (starting with drive letters like `C:` or root `/`).

---

## 11. Failure-State Implementation

Canonical response structures implemented:

### Successful Result
```json
{
  "status": "success",
  "dependency_map": { ... },
  "cycles": [ ... ],
  "error": null,
  "warnings": [],
  "metadata": {
    "madge_version": "8.0.0",
    "execution_time_ms": 110,
    "dependency_map_available": true,
    "cycles_available": true
  }
}
```

### Partial Result (e.g., dependency map parsed, cycle extraction crashed)
```json
{
  "status": "partial",
  "dependency_map": { ... },
  "cycles": null,
  "error": null,
  "warnings": [
    {
      "code": "MADGE_PARTIAL_OUTPUT",
      "message": "Circular dependency extraction was unsuccessful: ..."
    }
  ],
  "metadata": {
    "madge_version": "8.0.0",
    "execution_time_ms": 95,
    "dependency_map_available": true,
    "cycles_available": false
  }
}
```

### Failed Result
```json
{
  "status": "failed",
  "dependency_map": null,
  "cycles": null,
  "error": {
    "code": "MADGE_EXECUTION_FAILED",
    "message": "Madge returned non-zero exit code: ...",
    "retryable": false
  },
  "warnings": [],
  "metadata": { ... }
}
```

### Unavailable Result
```json
{
  "status": "unavailable",
  "dependency_map": null,
  "cycles": null,
  "error": {
    "code": "MADGE_NOT_FOUND",
    "message": "Madge executable is unavailable.",
    "retryable": false
  },
  "warnings": [],
  "metadata": { ... }
}
```

---

## 12. Canonical Error Codes

- `MADGE_NOT_FOUND`
- `MADGE_EXECUTION_FAILED`
- `MADGE_TIMEOUT`
- `MADGE_INVALID_JSON`
- `REPOSITORY_PATH_INVALID`
- `REPOSITORY_NOT_FOUND`
- `MADGE_PARTIAL_OUTPUT`

---

## 13. Unit and Integration Test Results

Ran `python -m pytest backend/tests/test_madge.py -v`:

```text
backend/tests/test_madge.py::test_executable_discovery PASSED            [  6%]
backend/tests/test_madge.py::test_missing_madge_executable PASSED        [ 13%]
backend/tests/test_madge.py::test_successful_dependency_map PASSED       [ 20%]
backend/tests/test_madge.py::test_empty_dependency_map PASSED            [ 26%]
backend/tests/test_madge.py::test_invalid_json_handling PASSED           [ 33%]
backend/tests/test_madge.py::test_nonzero_exit_code_handling PASSED      [ 40%]
backend/tests/test_madge.py::test_subprocess_timeout PASSED              [ 46%]
backend/tests/test_madge.py::test_invalid_repository_path PASSED         [ 53%]
backend/tests/test_madge.py::test_path_normalisation PASSED              [ 60%]
backend/tests/test_madge.py::test_circular_dependency_parsing PASSED     [ 66%]
backend/tests/test_madge.py::test_partial_extraction_handling PASSED     [ 73%]
backend/tests/test_madge.py::test_error_sanitization PASSED              [ 80%]
backend/tests/test_madge.py::test_subprocess_security_parameters PASSED  [ 86%]
backend/tests/test_madge.py::test_malformed_root_structure_rejected PASSED [ 93%]
backend/tests/test_madge.py::test_real_madge_integration_on_fixture PASSED [100%]

============================= 15 passed in 5.51s ==============================
```

- **Total Tests:** 15
- **Passed:** 15 (14 unit/mock tests + 1 real subprocess integration test)
- **Failed:** 0
- **Skipped:** 0

---

## 14. Known Limitations

1. **Dynamic / Runtime Imports:** Like all static dependency parsers, dynamic expressions (`import(variable)`) or complex runtime module loaders are not captured by Madge. This is documented and treated as inconclusive evidence.
2. **Framework Aliases:** Path aliases without standard `tsconfig.json` mappings might resolve partially. The runner handles this by falling back gracefully without crashing.

---

## 15. Files Created & Modified

### Files Created:
1. `backend/tests/fixtures/dependency_fixture/src/utils.ts`
2. `backend/tests/fixtures/dependency_fixture/src/app.ts`
3. `backend/tests/fixtures/dependency_fixture/src/main.ts`
4. `backend/tests/fixtures/dependency_fixture/src/services/auth.ts`
5. `backend/tests/fixtures/dependency_fixture/src/services/user.ts`
6. `backend/tests/fixtures/dependency_fixture/tests/app.test.ts`
7. `docs/implementation-plans/SAMAR_3_PHASE_2_IMPLEMENTATION_REPORT.md`

### Files Modified:
1. `tooling/package.json` (initialized with pinned `madge: "8.0.0"`)
2. `tooling/package-lock.json` (generated lockfile)
3. `backend/app/services/dependency_impact/madge_runner.py` (implemented complete runner)
4. `backend/app/services/dependency_impact/__init__.py` (re-exports)
5. `backend/tests/test_madge.py` (implemented 15 pytest tests)

---

## 16. Git Status Inspection

```powershell
On branch S
Untracked files:
  SAMAR_3_Detailed_Implementation_Plan.md
  backend/tests/fixtures/
  docs/implementation-plans/SAMAR_3_PHASE_1_INTEGRATION_CONTRACT.md
  docs/implementation-plans/SAMAR_3_PHASE_2_PRE_IMPLEMENTATION_VALIDATION.md
  docs/implementation-plans/SAMAR_3_PHASE_2_IMPLEMENTATION_REPORT.md
  tooling/package-lock.json

Changes not staged for commit:
  modified:   backend/app/services/dependency_impact/__init__.py
  modified:   backend/app/services/dependency_impact/madge_runner.py
  modified:   backend/tests/test_madge.py
  modified:   tooling/package.json
```

---

## 17. Readiness for Phase 3

The Madge Subprocess Runner is fully operational, verified, and battle-tested. It accurately parses dependencies and cycles, normalizes paths to repository-relative POSIX, protects against failures and timeouts, and is 100% ready to feed into **Phase 3: Graph Construction & Cycle Detection Engine**.

