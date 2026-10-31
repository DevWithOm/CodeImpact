# SAMAR_3: Dependency & Impact Engine
## Phase 5: Integration Contract Document
### Potential Test Impact Mapping & Entry-Point Intelligence

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Target Consumer:** TANUJA_4 (Orchestrator & Backend API)  
**Status:** LOCKED & EXPORT-READY  

---

## 1. Purpose & Integration Pipeline

This document defines the exact integration contract for Phase 5 Potential Test Impact Mapping.
The orchestrator (`backend/app/services/orchestrator.py`) should execute Phase 5 directly following Phase 4 finding-level impact analysis.

```text
Repository Workspace
         |
         v
Static Analysis (OM_2)
         |
         v
Madge Graph Construction (SAMAR_3 Phase 3)
         |
         v
Finding Impact Analysis (SAMAR_3 Phase 4)
         |
         v
Test Impact Mapping (SAMAR_3 Phase 5)  <--- THIS MODULE
         |
         v
Review Risk Engine (SAMAR_3 Phase 6)
         |
         v
API Response / Report Generator
```

---

## 2. Service Signature

```python
from backend.app.services.dependency_impact import analyze_test_impact

result = analyze_test_impact(
    graph: dict[str, Any] | BaseModel,
    enriched_findings: list[dict[str, Any]],
    repo_path: str | Path | None = None,
    analysis_id: str = "",
) -> dict[str, Any]:
```

### Input Parameters:
1. `graph` (required):
   The pre-constructed dependency graph dictionary or Pydantic `GraphData` / `DependencyGraphResponse` from Phase 3.
   **Crucial**: Phase 5 **never** invokes Madge, re-runs graph extraction, or modifies graph edges.
2. `enriched_findings` (required):
   List of finding dictionaries enriched by Phase 4 `analyze_impact()`.
   **Guaranteed**: Phase 5 deep-copies all input findings and preserves every existing field (`finding_id`, `file_path`, `category`, `direct_dependants`, `direct_dependencies`, `evidence`, `metadata`, etc.) without mutation.
3. `repo_path` (optional):
   Absolute local path to the workspace directory. Used solely for static inspection of `package.json` and directory structure (framework detection, entry points, filesystem test scanning).
4. `analysis_id` (optional):
   Unique analysis execution identifier string.

---

## 3. Response Contract

`analyze_test_impact()` returns a dictionary conforming to the Pydantic v2 `TestImpactAnalysisResult` schema:

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
      "mapping_status": "mapped",
      "impact_status": "success",
      "direct_dependants": [...],
      "direct_dependencies": [...],
      "summary": {...},
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
            "file_path": "tests/integration/checkout.test.ts",
            "test_type": "integration_test",
            "mapping_status": "heuristic",
            "evidence_type": "transitive_dependency",
            "dependency_path": [
              "tests/integration/checkout.test.ts",
              "src/services/order.ts",
              "src/services/payment.ts"
            ],
            "reason": "Test file reaches 'src/services/payment.ts' through intermediate dependencies (tests/integration/checkout.test.ts -> src/services/order.ts -> src/services/payment.ts)"
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

## 4. Enumerations & Permitted Values

| Field | Permitted Values |
| :--- | :--- |
| `status` (top-level & `test_impact`) | `"success"`, `"partial"`, `"unavailable"` |
| `mapping_status` (`TestCandidate`) | `"direct"`, `"heuristic"`, `"unknown"` |
| `test_type` (`TestCandidate`) | `"unit_test"`, `"integration_test"`, `"e2e_test"`, `"test_config"`, `"unknown_test_type"` |
| `evidence_type` (`TestCandidate`) | `"static_import"`, `"transitive_dependency"`, `"filename_match"`, `"directory_match"`, `"directory_and_filename_match"` |
| `confidence` (`FrameworkEvidence`) | `"high"`, `"medium"`, `"low"` |
| `entry_point_status` (`EntryPointEvidence`) | `"found"`, `"not_found"`, `"unknown"`, `"not_checked"` |
| `entry_point_type` (`EntryPointEvidence`) | `"application_entry"`, `"package_main"`, `"package_module"`, `"package_export"`, `"cli_bin"` |

---

## 5. Orchestrator Integration Example

```python
# In backend/app/services/orchestrator.py (TANUJA_4):

from backend.app.services.dependency_impact import (
    run_madge,
    build_dependency_graph,
    analyze_impact,
    analyze_test_impact,
)

# 1. Run Madge once
madge_result = run_madge(workspace_path)

# 2. Build dependency graph once
graph = build_dependency_graph(
    dependency_map=madge_result.get("dependency_map"),
    cycles=madge_result.get("cycles"),
    findings=om2_findings,
)

# 3. Analyze direct finding impact (Phase 4)
phase4_result = analyze_impact(
    graph=graph,
    findings=om2_findings,
    analysis_id=analysis_id,
)

# 4. Map potential test impact & entry points (Phase 5)
phase5_result = analyze_test_impact(
    graph=graph,
    enriched_findings=phase4_result["enriched_findings"],
    repo_path=workspace_path,
    analysis_id=analysis_id,
)

# Result now contains all Phase 4 + Phase 5 intelligence ready for Phase 6 (Review Risk)
```

