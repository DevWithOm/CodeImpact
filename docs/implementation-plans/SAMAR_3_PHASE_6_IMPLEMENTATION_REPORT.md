# SAMAR_3 — PHASE 6 IMPLEMENTATION REPORT
## Explainable Review-Risk Engine

**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Branch:** `S`  
**Status:** Complete & Fully Verified  

---

## 1. Executive Summary

Phase 6 implements the **Explainable Review-Risk Engine** for CodeImpact.
Building upon the verified foundations of Phases 1 through 5, this engine assesses how carefully human developers must inspect static analysis findings before refactoring or removing potentially unused code.

In strict adherence to CodeImpact's guiding principle:
> **"Not detected as used does not mean safe to delete."**

The Review-Risk Engine does **not** authorize code deletion or make automated refactoring edits. Instead, it provides deterministic, bounded ($0–100$) review priority scores, categorical classifications (`lower`, `medium`, `higher`, `unknown`), independent confidence ratings, stage completeness indicators, and fully transparent, factor-level explanations with actionable recommendations.

---

## 2. Implemented Modules & Schemas

### 2.1 Pydantic v2 Schemas (`backend/app/schemas/risk.py`)
- `RiskFactorBreakdown`: Detailed score contribution and supporting evidence for each individual factor.
- `RiskAssessment`: Structured container for completeness, factor breakdowns, positive factors, strict mitigating observations, uncertainties, and recommendations.
- `FindingRiskResult`: Finding-level review-risk envelope.
- `RiskSummary`: Repository-level statistics (total findings, assessed/unassessed counts, distribution across risk categories, average score excluding unknowns).
- `RiskAnalysisResult`: Top-level response schema for the review-risk engine.
- Re-exported in `backend/app/schemas/__init__.py`.

### 2.2 Core Engine Services (`backend/app/services/dependency_impact/`)
- `risk_scorer.py`:
  - `calculate_risk_score(finding, graph_is_available, entry_points)`: Evaluates factors F1 through F6, clamps the raw sum to $[0.0, 100.0]$, and applies thresholds.
  - `classify_risk(score, is_valid_assessment)`: Maps numeric scores to `lower` ($<30$), `medium` ($30–59$), `higher` ($\ge 60$), or `unknown` (for unmapped or unavailable graph states).
  - Individual factor scoring functions:
    - `score_dependency_exposure()`: Direct dependants (5 pts each up to 20; +5 breadth bonus if $\ge 5$ or spanning $\ge 2$ directories; max 25).
    - `score_cycle_exposure()`: Multi-file cycles (15 pts); self-loops only (4 pts); no cycle (0 pts); max 15.
    - `score_entry_point_exposure()`: Manifest entry (`package_main`/`bin` $\rightarrow 20$ pts); standard entry paths ($12$ pts); secondary heuristics ($5$ pts); max 20.
    - `score_test_impact_evidence()`: Direct candidate test ($15$ pts); transitive candidate ($10$ pts); heuristic match ($6$ pts); no tests ($0$ pts; **never** subtracts or lowers risk); max 15.
    - `score_finding_evidence()`: `unused_export` ($10$ pts); `duplicate_code` ($8$ pts); `unused_file` ($5$ pts); inconclusive evidence penalty ($+5$ pts); max 15.
    - `score_structural_exposure()`: Outbound coupling $\ge 5$ ($+5$ pts); core architectural directory ($+5$ pts); max 10.
- `risk_explainer.py`:
  - `generate_positive_factors()`: Articulates all factors that increase review priority.
  - `generate_mitigating_observations()`: Generates mitigations **only** when graph is available and complete (`truncated == False`). Strictly prohibits classifying "no tests found" as a mitigation.
  - `generate_uncertainties()`: Discloses limitations (e.g. lack of dynamic import detection, lack of runtime assertion coverage in tests, graph truncation).
  - `generate_recommendation()`: Produces specific, evidence-driven instructions for developer manual review.
- `risk_analyzer.py`:
  - `analyze_review_risk(graph, enriched_findings, entry_points, analysis_id)`: Main service coordinator.
  - Deep-copies input findings ensuring complete immutability.
  - Computes `risk_confidence` (`high`, `medium`, `low`, `unknown`) and `analysis_completeness` (`complete`, `partial`, `unavailable`).
  - Aggregates accurate repository-level summary metrics.
- Re-exported via `backend/app/services/dependency_impact/__init__.py`.

---

## 3. Representative Output Example

```json
{
  "finding_id": "f_101",
  "file_path": "src/services/payment.ts",
  "category": "unused_export",
  "mapping_status": "mapped",
  "impact_status": "success",
  "direct_dependants": [
    {"file_path": "src/api/checkout.ts"},
    {"file_path": "src/workers/billing.ts"},
    {"file_path": "src/admin/portal.ts"}
  ],
  "direct_dependencies": [
    {"file_path": "src/utils/logger.ts"}
  ],
  "cycle_member": true,
  "cycles": [
    ["src/services/payment.ts", "src/services/order.ts", "src/services/payment.ts"]
  ],
  "self_dependency_detected": false,
  "test_impact": {
    "status": "success",
    "mapping_complete": true,
    "candidate_tests": [
      {
        "file_path": "tests/payment.test.ts",
        "mapping_status": "direct",
        "evidence_type": "static_import"
      }
    ],
    "summary": {
      "direct_test_count": 1,
      "heuristic_test_count": 0,
      "unknown_test_count": 0
    }
  },
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
      "Candidate test files directly import this module.",
      "Flagged symbol is an export; external consumers or dynamic imports may rely on it.",
      "Module resides in core architectural directory."
    ],
    "mitigating_observations": [],
    "uncertainties": [
      "Static dependency analysis cannot detect dynamic import() expressions, reflection, or external consumers.",
      "Identified candidate tests do not establish runtime assertion or code coverage."
    ],
    "recommendation": "Carefully review all 3 direct dependant(s), inspect and decouple circular dependency chain, inspect potentially related candidate tests before making any refactoring or deletion decisions."
  }
}
```

---

## 4. Test Suite Execution Results

All unit and regression tests pass without warnings:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1
collected 173 items

backend/tests/test_cycle_detector.py::... PASSED
backend/tests/test_entry_point_detector.py::... PASSED
backend/tests/test_finding_mapper.py::... PASSED
backend/tests/test_graph_builder.py::... PASSED
backend/tests/test_impact_analyzer.py::... PASSED
backend/tests/test_madge.py::... PASSED
backend/tests/test_test_discovery.py::... PASSED
backend/tests/test_test_framework_detector.py::... PASSED
backend/tests/test_test_impact_analyzer.py::... PASSED
backend/tests/test_test_mapper.py::... PASSED
backend/tests/test_risk_scorer.py::... PASSED (20 tests)
backend/tests/test_risk_explainer.py::... PASSED (8 tests)
backend/tests/test_risk_analyzer.py::... PASSED (5 tests)

============================= 173 passed in 11.48s ==============================
```

- **Previous Baseline**: 140 passed.
- **Phase 6 Additions**: 33 passed.
- **Total Passing Tests**: 173 passed, 0 failed, 0 warnings.

---

## 5. Acceptance Criteria Verification

| ID | Criterion | Status | Verification Detail |
| :--- | :--- | :---: | :--- |
| P6-01 | Existing Phase 1–5 functionality intact | PASS | All 140 prior tests pass with zero regressions. |
| P6-02 | Signals extracted from actual schemas | PASS | Directly utilizes Phase 3 graph, Phase 4 dependants/cycles, and Phase 5 test candidates/entry points. |
| P6-03 | Scoring is deterministic | PASS | Verified in `test_determinism_across_multiple_runs`. |
| P6-04 | Score bounded 0–100 | PASS | Clamped mathematically via $\min(100, \max(0, \sum F_i))$. |
| P6-05 | Documented thresholds | PASS | Verified in `test_classify_risk_threshold_boundaries`. |
| P6-06 | Confidence separate from risk level | PASS | Modeled independently via `risk_confidence`. |
| P6-07 | Completeness separate from confidence and risk | PASS | Modeled independently via `analysis_completeness`. |
| P6-08 | Dependency exposure calculated transparently | PASS | Verified in `TestDependencyExposureScoring`. |
| P6-09 | Self-loops distinguished from cycles | PASS | Self-loop = 4 pts; multi-file cycle = 15 pts. |
| P6-10 | Test impact considered without claiming coverage | PASS | Modeled as review urgency indicator. |
| P6-11 | Absence of tests does not reduce risk | PASS | Verified in `test_absence_of_tests_never_reduces_score`. |
| P6-12 | Entry points affect review priority | PASS | Manifest and canonical entry points scored appropriately. |
| P6-13 | Missing evidence avoids false reassurance | PASS | Missing graph/unmapped yields `review_risk == "unknown"`, `risk_score = None`. |
| P6-14 | Truncated graphs handled properly | PASS | Mitigations suppressed; confidence set to `low`. |
| P6-15 | Factor-level explanations generated | PASS | Every assessed finding contains detailed `factor_breakdown`. |
| P6-16 | Uncertainties cataloged | PASS | Discloses dynamic imports and lack of coverage claims. |
| P6-17 | Original findings unmodified | PASS | Verified in `test_findings_are_not_mutated`. |
| P6-18 | Pydantic serialization verified | PASS | All outputs conform to `RiskAnalysisResult`. |
| P6-19 | Summary counts accurate | PASS | Verified counts for total, assessed, unassessed, and categories. |
| P6-20 | Public service exported and documented | PASS | `analyze_review_risk` exported from `dependency_impact`. |
| P6-21 | Existing tests pass | PASS | 140/140 passed. |
| P6-22 | Phase 6 tests pass | PASS | 33/33 passed. |
| P6-23 | No target code executed | PASS | Zero subprocess or eval execution of repo code. |
| P6-24 | Integration contract ready | PASS | `SAMAR_3_PHASE_6_INTEGRATION_CONTRACT.md` delivered. |
| P6-25 | Within time budget | PASS | Completed within 4-hour allocation. |

