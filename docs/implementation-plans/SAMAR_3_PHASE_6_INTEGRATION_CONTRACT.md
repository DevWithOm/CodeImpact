# SAMAR_3 — PHASE 6 INTEGRATION CONTRACT
## Explainable Review-Risk Engine Integration for TANUJA_4

**Author:** SAMAR_3 (Dependency & Impact Engine)  
**Consumer:** TANUJA_4 (AI Assistant, Backend Integration, Orchestrator)  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Module:** `backend/app/services/dependency_impact/`  
**Status:** Approved for Orchestrator Integration  

---

## 1. Architecture & Pipeline Location

The Explainable Review-Risk Engine is the **final deterministic processing stage** in the Dependency & Impact pipeline. It executes immediately following Phase 5 (Potential Test Impact Mapping) and consumes:
1. The Phase 3 Dependency Graph.
2. The Phase 5 Enriched Findings (containing Phase 4 direct impacts and Phase 5 candidate tests).
3. The Phase 5 Detected Entry Points.

```text
                  Phase 1 Raw Findings (OM_2)
                              |
                              v
             Phase 2 Madge Runner (Subprocess)
                              |
                              v
             Phase 3 Dependency Graph Construction
                              |
                              v
             Phase 4 Finding-Level Impact Analysis
                              |
                              v
             Phase 5 Potential Test Impact Mapping
                              |
                              v
         ==> PHASE 6 EXPLAINABLE REVIEW-RISK ENGINE <==
                              |
                              v
                 Final Enriched Findings Payload
            (Consumed by API, Reports, and Frontend)
```

---

## 2. Public Service Interface

The public function is exposed from `backend.app.services.dependency_impact`:

```python
def analyze_review_risk(
    graph: dict[str, Any] | BaseModel | None = None,
    enriched_findings: list[dict[str, Any]] | None = None,
    entry_points: list[dict[str, Any]] | None = None,
    analysis_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    ...
```

### Parameters:
- `graph` (`dict | BaseModel | None`): The pre-constructed dependency graph from Phase 3.
- `enriched_findings` (`list[dict]`): The list of findings enriched through Phase 4 and Phase 5.
- `entry_points` (`list[dict] | None`): Optional list of detected application/package entry points from Phase 5 `entry_points`.
- `analysis_id` (`str`): Unique tracking identifier for the analysis session.

---

## 3. Input Contract Requirements

Each finding dictionary in `enriched_findings` should ideally include:
```json
{
  "finding_id": "string",
  "category": "unused_export | unused_file | duplicate_code | ...",
  "file_path": "string (repository-relative POSIX path)",
  "mapping_status": "mapped | unmapped | invalid_path | missing_file_path",
  "impact_status": "success | partial | unavailable",
  "direct_dependants": [
    { "file_path": "string" }
  ],
  "direct_dependencies": [
    { "file_path": "string" }
  ],
  "cycle_member": true | false,
  "cycles": [
    ["path_a", "path_b", "path_a"]
  ],
  "self_dependency_detected": true | false,
  "test_impact": {
    "status": "success | partial | unavailable",
    "mapping_complete": true | false,
    "candidate_tests": [
      {
        "file_path": "string",
        "mapping_status": "direct | heuristic | unknown",
        "evidence_type": "static_import | transitive_dependency | filename_match | directory_match"
      }
    ],
    "summary": {
      "direct_test_count": 0,
      "heuristic_test_count": 0,
      "unknown_test_count": 0
    }
  }
}
```

*Note on Missing Inputs:* If `test_impact` or `entry_points` are omitted or partial, the engine handles them gracefully without raising exceptions, setting confidence ratings accordingly and preserving uncertainties.

---

## 4. Output Contract (`RiskAnalysisResult`)

The returned dictionary conforms to `backend.app.schemas.risk.RiskAnalysisResult`:

```json
{
  "analysis_id": "run_001",
  "status": "success",
  "enriched_findings": [
    {
      "finding_id": "f_001",
      "file_path": "src/services/payment.ts",
      "review_risk": "higher",
      "risk_score": 70.0,
      "risk_confidence": "high",
      "risk_assessment": {
        "analysis_completeness": "complete",
        "factor_breakdown": [
          {
            "factor": "dependency_exposure",
            "score": 20.0,
            "maximum_score": 25.0,
            "observed_value": 3,
            "status": "evaluated",
            "reason": "3 direct dependants import this file across 3 directory structures.",
            "evidence": ["src/api/checkout.ts", "src/workers/billing.ts", "src/admin/portal.ts"]
          },
          {
            "factor": "cycle_exposure",
            "score": 15.0,
            "maximum_score": 15.0,
            "observed_value": "multi_file_cycle",
            "status": "evaluated",
            "reason": "Module is a member of 1 multi-file dependency cycle(s).",
            "evidence": [["src/services/payment.ts", "src/services/order.ts", "src/services/payment.ts"]]
          },
          {
            "factor": "entry_point_exposure",
            "score": 0.0,
            "maximum_score": 20.0,
            "observed_value": "not_entry_point",
            "status": "evaluated",
            "reason": "File was not identified as an application or module entry point.",
            "evidence": []
          },
          {
            "factor": "test_impact_evidence",
            "score": 15.0,
            "maximum_score": 15.0,
            "observed_value": "direct_test_candidate",
            "status": "evaluated",
            "reason": "1 candidate test(s) directly import this source module.",
            "evidence": ["tests/payment.test.ts"]
          },
          {
            "factor": "finding_evidence_uncertainty",
            "score": 15.0,
            "maximum_score": 15.0,
            "observed_value": {"category": "unused_export", "evidence_class": "inconclusive"},
            "status": "evaluated",
            "reason": "Exported symbol carries external consumer and dynamic import risk.; Static scan evidence is inconclusive; heightened review uncertainty.",
            "evidence": []
          },
          {
            "factor": "special_structural_exposure",
            "score": 5.0,
            "maximum_score": 10.0,
            "observed_value": {"out_degree": 1, "path": "src/services/payment.ts"},
            "status": "evaluated",
            "reason": "Module resides in core architectural directory.",
            "evidence": []
          }
        ],
        "positive_factors": [
          "3 files directly import this module.",
          "Module participates in a multi-file circular dependency.",
          "Candidate test files directly import this module."
        ],
        "mitigating_observations": [],
        "uncertainties": [
          "Static dependency analysis cannot detect dynamic import() expressions, reflection, or external consumers.",
          "Identified candidate tests do not establish runtime assertion or code coverage."
        ],
        "recommendation": "Carefully review all 3 direct dependant(s), inspect and decouple circular dependency chain, inspect potentially related candidate tests before making any refactoring or deletion decisions."
      }
    }
  ],
  "summary": {
    "total_findings": 1,
    "assessed_findings": 1,
    "unassessed_findings": 0,
    "higher_risk_count": 1,
    "medium_risk_count": 0,
    "lower_risk_count": 0,
    "unknown_risk_count": 0,
    "average_risk_score": 70.0
  }
}
```

---

## 5. Orchestrator Integration Pattern for TANUJA_4

```python
from backend.app.services.dependency_impact import (
    run_madge,
    build_dependency_graph,
    analyze_impact,
    analyze_test_impact,
    analyze_review_risk,
)

def run_analysis_pipeline(repo_path: str, raw_findings: list[dict], analysis_id: str) -> dict:
    # 1. Run Madge subprocess
    madge_result = run_madge(repo_path)

    # 2. Build Dependency Graph
    graph_response = build_dependency_graph(
        dependency_map=madge_result.get("dependency_map"),
        cycles=madge_result.get("cycles"),
        findings=raw_findings,
    )
    graph = graph_response.get("graph")

    # 3. Phase 4: Finding-Level Impact Analysis
    phase4_result = analyze_impact(
        graph=graph,
        findings=raw_findings,
        analysis_id=analysis_id,
    )

    # 4. Phase 5: Potential Test Impact Mapping
    phase5_result = analyze_test_impact(
        graph=graph,
        enriched_findings=phase4_result.get("enriched_findings", []),
        repo_path=repo_path,
        analysis_id=analysis_id,
    )

    # 5. Phase 6: Explainable Review-Risk Engine
    phase6_result = analyze_review_risk(
        graph=graph,
        enriched_findings=phase5_result.get("enriched_findings", []),
        entry_points=phase5_result.get("entry_points", []),
        analysis_id=analysis_id,
    )

    # Final enriched findings with full risk assessment attached
    return {
        "analysis_id": analysis_id,
        "graph": graph,
        "frameworks": phase5_result.get("detected_frameworks", []),
        "entry_points": phase5_result.get("entry_points", []),
        "enriched_findings": phase6_result.get("enriched_findings", []),
        "risk_summary": phase6_result.get("summary", {}),
    }
```

---

## 6. Ownership Boundaries

- **SAMAR_3 Ownership**:
  - `backend/app/schemas/risk.py`
  - `backend/app/services/dependency_impact/risk_scorer.py`
  - `backend/app/services/dependency_impact/risk_explainer.py`
  - `backend/app/services/dependency_impact/risk_analyzer.py`
  - `backend/app/services/dependency_impact/__init__.py`
  - `backend/tests/test_risk_*.py`
- **TANUJA_4 Ownership**:
  - `backend/app/services/orchestrator.py`
  - Top-level report formatting and AI assistant explanations.
  - API endpoint integration.

