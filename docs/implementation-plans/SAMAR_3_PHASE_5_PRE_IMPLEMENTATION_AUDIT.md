# SAMAR_3: Dependency & Impact Engine
## Phase 5: Pre-Implementation Audit Document
### Potential Test Impact Mapping & Entry-Point Intelligence

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (Pre-Implementation Baseline Locked)  

---

## 1. Executive Summary

Phase 5 introduces **Potential Test Impact Mapping** into CodeImpact's Dependency & Impact Engine.
When static analysis flags a source file (e.g. `src/services/payment.ts`), CodeImpact must identify candidate test files that could be affected if that source file is refactored, changed, or deleted.

Crucially, in alignment with CodeImpact's core tenet—*"Not detected as used does not mean safe to delete"*—Phase 5 maintains absolute transparency:
- **Direct import evidence** is strictly separated from **heuristic similarity** and **transitive reachability**.
- The engine **never claims test coverage**, behavioral validity, or runtime test outcomes.
- All discovery, framework identification, and entry-point analysis are strictly static (no execution of untrusted repository code, scripts, or package managers).

---

## 2. Existing Baseline & Architecture Inspection

### 2.1 Reused Components (Phases 1–4)
1. **`madge_runner.py`**:
   - Pinned `madge@8.0.0` with `shell=False` and bounded 5MB streaming.
   - Robust path normalization (`normalize_repo_relative_path`) enforcing POSIX `/`, rejecting path traversal (`..`), and preventing host path leaks.
2. **`graph_builder.py`**:
   - Directed graph representation: `source -> target` means **source imports target**.
   - Edge IDs: Canonical `"{source}->{target}"`.
   - Node identifiers: Canonical repository-relative POSIX path.
   - Cycle detection & membership sets via `cycle_detector.py`.
   - Truncation tracking: Pre-truncation statistics and deterministic top-$N$ truncation.
3. **`impact_analyzer.py` & `finding_mapper.py`**:
   - Indexed graph lookups (`incoming_edges`, `outgoing_edges`).
   - Direct dependants (incoming edges) and dependencies (outgoing edges).
   - Preservation of all original OM_2 finding fields and deep copying.
   - Clean status distinction: `success`, `partial` (e.g. truncated graphs), and `unavailable` (system failure/missing graph).
4. **Current Test Suite**:
   - 109/109 passing pytest tests with 0 failures and 0 warnings.

### 2.2 Integration State of Orchestrator
Inspection of `backend/app/services/orchestrator.py` reveals it remains a placeholder owned by **TANUJA_4**. SAMAR_3 exposes decoupled, pure-function services that can be chained cleanly by TANUJA_4 or called standalone.

---

## 3. Findings from Audit

1. **Test Nodes in Dependency Graph**:
   - In JavaScript/TypeScript codebases, test files (e.g. `tests/app.test.ts`) are frequently parsed by Madge if they reside within the analyzed workspace.
   - However, some test files might not import source files directly (e.g. testing via global fixtures, integration runners, or dynamic requires), or may be excluded if Madge was run on a subfolder.
   - **Requirement**: Use graph edges as the primary source of truth for `direct` mappings, and supplement with directory and naming heuristics for `heuristic` mappings.
2. **Directionality Invariant**:
   - If test file `T` imports source file `S`, the directed edge is `T -> S`.
   - `T` is an incoming edge source to `S` (`edge.source == T`, `edge.target == S`).
   - For a finding on `S`, `T` is a direct incoming importer.
3. **Transitive Test Reachability**:
   - When `T -> index.ts -> S`, `T` reaches `S` through an intermediate module.
   - Must be bounded by `MAX_TEST_IMPACT_DEPTH` (default: 5) and cycle-aware using a visited set to avoid infinite loops.
   - Must be labeled `mapping_status = "heuristic"`, `evidence_type = "transitive_dependency"`.
4. **Static Framework & Entry-Point Detection**:
   - Framework detection should statically inspect configuration files (`jest.config.*`, `vitest.config.*`, `playwright.config.*`, `package.json`).
   - Entry-point detection should statically inspect `package.json` (`main`, `module`, `exports`, `bin`, `scripts`) and standard entry paths (`src/index.*`, `src/main.*`, `server.ts`).

---

## 4. Proposed Phase 5 Modular Structure

```text
backend/app/
  schemas/
    test_impact.py          # Pydantic v2 schemas for test impact, frameworks, entry points
  services/
    dependency_impact/
      test_discovery.py           # Static test file discovery & classification
      test_framework_detector.py  # Static testing framework detection
      entry_point_detector.py     # Static application entry point detection
      test_mapper.py              # Direct, transitive, and heuristic test matching
      test_impact_analyzer.py     # Top-level service coordinating Phase 5 pipeline
```

---

## 5. Risk Assessment & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **Infinite cycles during transitive traversal** | Maintain a per-traversal `visited` node set and enforce `MAX_TEST_IMPACT_DEPTH = 5`. |
| **Path traversal / security escape** | Use `normalize_repo_relative_path` on all discovered and computed paths. Ignore `.git`, `node_modules`, `dist`, `build`. |
| **Execution of untrusted code** | Pure text/JSON inspection only. Never evaluate `.js`/`.ts` configuration files or run package scripts. |
| **Overstated coverage claims** | Strictly categorize mapping strength (`direct`, `heuristic`, `unknown`) and use non-coverage terminology. |
| **Duplicate test results** | Deduplicate candidates per finding, retaining the strongest relationship (`direct` > `heuristic`). |

