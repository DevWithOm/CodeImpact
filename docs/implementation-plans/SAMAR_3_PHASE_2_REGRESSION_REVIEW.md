# SAMAR_3: Dependency & Impact Engine
## Phase 2 Regression Review: Subprocess Output Limits & Windows Execution Reliability

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** PASS WITH FIXES (All 35 Unit and Real Windows Integration Tests Passing)  
**Project Root:** `C:\DeadCode`  
**Target Module:** `backend/app/services/dependency_impact/madge_runner.py`  

---

## 1. Review Objective

Conduct a rigorous regression review and targeted hardening of two specific engineering concerns:
1. **Subprocess Output Memory Protection:** Verify whether the 5 MB stream limit was actively enforced while Madge executes or only sliced post-completion.
2. **Windows Execution Reliability:** Ensure that Madge executes deterministically and securely on Windows with `shell=False`, immune to batch wrapper quirks, quoting errors, and spaces in file paths.

---

## 2. Files Inspected

- `backend/app/services/dependency_impact/madge_runner.py`
- `backend/app/services/dependency_impact/__init__.py`
- `backend/tests/test_madge.py`
- `tooling/package.json`
- `tooling/package-lock.json`
- `docs/implementation-plans/SAMAR_3_PHASE_2_IMPLEMENTATION_REPORT.md`

---

## 3. Inspection Findings & Initial State Analysis

| Check | Initial Implementation | Assessment | Finding / Evidence |
| :--- | :--- | :---: | :--- |
| **Output Limit Enforcement** | `subprocess.run(capture_output=True)` followed by `stdout[:MAX_OUTPUT_BYTES]` | **FAIL (Post-execution only)** | Initial code allowed the child process to buffer unlimited output in memory before slicing. |
| **Memory Protection** | Post-execution string truncation | **FAIL** | If a subprocess emitted 1 GB of data, host memory was exhausted during `subprocess.run()`. |
| **Timeout Handling** | `subprocess.TimeoutExpired` caught | **PASS** | Terminated after deadline. |
| **Windows Invocation** | Invoked `madge.cmd` directly with `shell=False` | **PARTIAL** | Python on Windows can run `.cmd` via cmd proxy, but is vulnerable to quoting bugs, path spaces, and signal trapping. |
| **`shell=False`** | Explicitly set to `False` | **PASS** | Argument list passed without shell interpolation. |
| **Node.js Fallback** | Unused; depended on `.cmd` wrapper | **PARTIAL** | Did not leverage installed Node.js binary directly. |

---

## 4. Hardening 1: Genuine Bounded In-Flight Streaming Output

### Initial Flaw:
The initial implementation used `subprocess.run(..., capture_output=True)` and truncated stdout after the process completed (`stdout_raw = proc.stdout[:MAX_OUTPUT_BYTES]`).

### Final Bounded Implementation:
Replaced with `run_subprocess_bounded()`:
1. Spawns `subprocess.Popen` with `stdout=subprocess.PIPE` and `stderr=subprocess.PIPE`.
2. Reads stdout and stderr concurrently via dedicated daemon threads in 64 KB chunks.
3. Tracks byte count incrementally: if either stream exceeds `max_output_bytes` (5 MB default), an `overflow_event` is fired immediately.
4. The main thread loop immediately detects overflow, terminates the child process, and reaps it cleanly without leaking zombie processes.
5. Returns `status="failed"`, `error.code="MADGE_OUTPUT_LIMIT_EXCEEDED"`.
6. Output-limit failures are never converted into successful empty graphs or corrupted partial models.

---

## 5. Hardening 2: Windows Native Node.js Invocation Strategy

### Initial Flaw:
Invoking `tooling/node_modules/.bin/madge.cmd` relied on Windows batch script execution. Batch scripts on Windows do not handle process signals cleanly, can misinterpret arguments containing spaces, and introduce Windows command shell dependencies.

### Final Invocation Strategy:
Implemented direct Node.js execution via `resolve_madge_command()`:
1. Discovers Node.js executable directly via `find_node_executable()` (`node.exe` or `node`).
2. Discovers the installed JavaScript CLI entry point under `tooling/node_modules/madge/bin/cli.js` via `find_madge_entrypoint()`.
3. Constructs argument list directly:
   ```python
   [node_bin, cli_js_path, "--extensions", "ts,tsx,js,jsx", "--json", "."]
   ```
4. Executes directly via `subprocess.Popen(..., shell=False)`.
5. **Advantages:**
   - Native Windows `.exe` execution: no `cmd.exe` or batch wrapper overhead.
   - Immune to argument quoting errors or spaces in directory paths (verified via test).
   - Clean signal handling and immediate process termination on overflow or timeout.
   - Identical execution model across Windows, Linux, and macOS.

---

## 6. Error-Handling Contract Updates

Added canonical error code:
```text
ERR_MADGE_OUTPUT_LIMIT_EXCEEDED = "MADGE_OUTPUT_LIMIT_EXCEEDED"
```

When stream limit is exceeded:
```json
{
  "status": "failed",
  "dependency_map": null,
  "cycles": null,
  "error": {
    "code": "MADGE_OUTPUT_LIMIT_EXCEEDED",
    "message": "Madge output stream exceeded maximum allowed limit of 5242880 bytes.",
    "retryable": false
  },
  "warnings": []
}
```

---

## 7. Full Test Suite & Regression Results

Ran: `python -m pytest backend/tests/test_madge.py -v`

### Summary:
- **Total Tests:** 35
- **Passed:** 35 (100%)
- **Failed:** 0
- **Execution Time:** 8.00s

### Breakdown:
1. **Original 15 Tests (Preserved & Passing):**
   - Executable discovery, missing executable, successful map parsing, empty map handling, invalid JSON, non-zero exit codes, timeout handling, invalid repo path, path normalisation & traversal rejection, cycle parsing, partial extraction, error sanitisation, subprocess argument parameters, malformed JSON rejection, and real fixture integration.
2. **10 Output-Limit & Memory-Protection Tests (New):**
   - `test_stdout_below_limit`: Stdout within limits succeeds.
   - `test_stderr_below_limit`: Stderr within limits succeeds.
   - `test_stdout_exceeding_limit`: Stdout overflow triggers termination and error.
   - `test_stderr_exceeding_limit`: Stderr overflow triggers termination and error.
   - `test_concurrent_large_streams_no_deadlock`: Concurrent writing does not deadlock pipes.
   - `test_valid_json_below_limit_parsed`: Valid JSON within bounds parses.
   - `test_truncated_json_overflow_is_failure`: Truncated JSON returns `MADGE_OUTPUT_LIMIT_EXCEEDED`.
   - `test_timeout_during_output_streaming`: Streaming timeout terminates process.
   - `test_cleanup_after_output_overflow`: Child process killed on overflow.
   - `test_cleanup_after_timeout`: Child process killed on timeout.
3. **10 Windows & Node.js Execution Tests (New):**
   - `test_node_executable_discovery`: Node.js found on PATH.
   - `test_local_madge_entrypoint_discovery`: `cli.js` entrypoint located.
   - `test_resolve_madge_command_uses_node`: Resolves `[node, cli.js]`.
   - `test_invocation_shell_false_contract`: Strictly verifies `shell=False`.
   - `test_repository_path_with_spaces`: Verified real execution in directory path with spaces.
   - `test_working_directory_handling`: Verified repository `cwd` parameter.
   - `test_real_madge_fixture_dependency_map`: Real Madge dependency extraction.
   - `test_real_madge_fixture_circular_dependencies`: Real Madge circular extraction.
   - `test_missing_node_executable`: Graceful `unavailable` on missing Node.
   - `test_missing_madge_installation`: Graceful `unavailable` on missing Madge.

---

## 8. Real Windows Fixture Verification Evidence

Real integration tests (`test_real_madge_integration_on_fixture`, `test_real_madge_fixture_dependency_map`, `test_real_madge_fixture_circular_dependencies`) were executed against `backend/tests/fixtures/dependency_fixture/`:

### Dependency Map Verified:
```json
{
  "src/app.ts": ["src/utils.ts"],
  "src/main.ts": ["src/app.ts"],
  "src/services/auth.ts": ["src/services/user.ts"],
  "src/services/user.ts": ["src/services/auth.ts"],
  "src/utils.ts": [],
  "tests/app.test.ts": ["src/app.ts"]
}
```

### Circular Dependencies Verified:
```json
[
  ["src/services/auth.ts", "src/services/user.ts"]
]
```

---

## 9. Security & Resource Validation Checklist

| Requirement | Status | Verification |
| :--- | :---: | :--- |
| `shell=False` | **Mandatory & Verified** | All subprocess calls pass explicit argument lists with `shell=False`. |
| Stdout bounded during execution | **Mandatory & Verified** | Bounded streaming reader kills process on buffer overflow. |
| Stderr bounded during execution | **Mandatory & Verified** | Bounded streaming reader kills process on buffer overflow. |
| Timeout enforcement | **Mandatory & Verified** | In-flight deadline kills process on timeout. |
| Process termination & cleanup | **Mandatory & Verified** | `proc.terminate()` and `proc.kill()` ensure zero zombie processes. |
| No unlimited communicate buffering | **Mandatory & Verified** | Replaced `capture_output=True` with in-flight thread streaming. |
| No target package scripts executed | **Mandatory & Verified** | Target repository files are analyzed strictly as static text. |
| No target dependencies installed | **Mandatory & Verified** | Dependencies installed exclusively in `tooling/`. |
| No shell command construction | **Mandatory & Verified** | Argument lists used exclusively; no string formatting. |
| No hardcoded machine paths | **Mandatory & Verified** | Relative discovery and path sanitization applied. |
| Existing API contract preserved | **Mandatory & Verified** | All function signatures and return structures preserved. |

---

## 10. Files Modified

1. `backend/app/services/dependency_impact/madge_runner.py` — In-flight bounded streaming runner and direct Node.js entry point resolution.
2. `backend/app/services/dependency_impact/__init__.py` — Re-exported new interfaces and `ERR_MADGE_OUTPUT_LIMIT_EXCEEDED`.
3. `backend/tests/test_madge.py` — Extended from 15 to 35 unit, regression, and Windows integration tests.
4. `docs/implementation-plans/SAMAR_3_PHASE_2_REGRESSION_REVIEW.md` — Created review document.

---

## 11. Remaining Limitations

1. **Subprocess Thread Overhead:** Two lightweight daemon reader threads per invocation. Given that Madge is run per repository analysis (not in a tight micro-loop), the resource footprint is negligible and provides ironclad memory guarantees.
2. **Dynamic Imports:** As with all static analysis, runtime dynamic expressions (`import(variable)`) are omitted by Madge.

---

## 12. Final Verdict

**PASS WITH FIXES**  
Both concerns (in-flight memory bounds and Windows `shell=False` reliability) have been thoroughly investigated, fixed, tested, and validated on the Windows environment with 35/35 passing tests.

