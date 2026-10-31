# SAMAR_3 — PHASE 6 IMPLEMENTATION PLAN
## Explainable Review-Risk Engine

**Author:** SAMAR_3 (Dependency & Impact Engine)  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Time Allocation:** Max 4 Hours (240 Minutes)  
**Status:** Approved for Implementation  

---

## 1. Objectives & Scope

Phase 6 implements the **Explainable Review-Risk Engine** for CodeImpact.
The engine consumes Phase 3 graphs, Phase 4 impact findings, and Phase 5 test-impact models to synthesize a deterministic review-risk score ($0–100$), categorical risk level, confidence rating, completeness status, factor breakdown, and actionable human recommendations.

### In Scope
1. Creation of Pydantic v2 schemas in `backend/app/schemas/risk.py`:
   - `RiskFactorBreakdown`
   - `RiskAssessment`
   - `FindingRiskResult`
   - `RiskSummary`
   - `RiskAnalysisResult`
2. Core Engine Services in `backend/app/services/dependency_impact/`:
   - `risk_scorer.py`: Extraction of signals, deterministic scoring across 6 factors, score clamping $[0, 100]$, and threshold classification.
   - `risk_explainer.py`: Generation of factor-level reasons, positive factors, strict mitigating observations, uncertainties, and tailored recommendations.
   - `risk_analyzer.py`: Orchestrator of Phase 6, computing per-finding confidence, completeness, attaching risk payloads without mutating originals, and producing summary metrics.
   - `__init__.py`: Export public functions and models.
3. Dedicated Unit & Regression Test Suite:
   - `backend/tests/test_risk_scorer.py`
   - `backend/tests/test_risk_explainer.py`
   - `backend/tests/test_risk_analyzer.py`
4. Documentation deliverables in `docs/implementation-plans/`.

### Out of Scope
- Re-running Madge or modifying Phase 2 runner.
- Modifying Phase 3 graph builder or Phase 4/5 logic.
- Rewriting TANUJA_4's `orchestrator.py`.
- LLM inference, machine learning, or probabilistic models.
- Target repository code or test execution.

---

## 2. Work Breakdown & Time Budget

| Step | Task | Target Duration |
| :---: | :--- | :---: |
| **Step 1** | Audit, Model Specification, and Implementation Plan | 35 mins |
| **Step 2** | Pydantic v2 Schemas (`backend/app/schemas/risk.py`) | 20 mins |
| **Step 3** | Risk Scorer (`backend/app/services/dependency_impact/risk_scorer.py`) | 40 mins |
| **Step 4** | Risk Explainer (`backend/app/services/dependency_impact/risk_explainer.py`) | 35 mins |
| **Step 5** | Risk Analyzer & Top-Level Service (`risk_analyzer.py` & `__init__.py`) | 30 mins |
| **Step 6** | Unit and Integration Tests (`backend/tests/test_risk_*.py`) | 45 mins |
| **Step 7** | Regression Run (All 140+ Tests) & Final Audit | 20 mins |
| **Step 8** | Implementation Report & Integration Contract | 15 mins |
| **Total** | | **240 mins (4.0 hrs)** |

---

## 3. Schema Design

File: `backend/app/schemas/risk.py`
```python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class RiskFactorBreakdown(BaseModel):
    factor: str = Field(description="Factor identifier")
    score: float = Field(ge=0, le=100, description="Points contributed by this factor")
    maximum_score: float = Field(ge=0, le=100, description="Maximum possible points for factor")
    observed_value: Any | None = Field(default=None, description="Observed metric value")
    status: str = Field(default="evaluated", description="Factor status: 'evaluated', 'not_applicable', 'unavailable'")
    reason: str = Field(default="", description="Human-readable justification")
    evidence: list[Any] = Field(default_factory=list, description="Traceable supporting evidence items")
    model_config = ConfigDict(extra="allow")

class RiskAssessment(BaseModel):
    analysis_completeness: str = Field(default="complete", description="'complete', 'partial', 'unavailable'")
    factor_breakdown: list[RiskFactorBreakdown] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    mitigating_observations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    recommendation: str = Field(default="")
    model_config = ConfigDict(extra="allow")

class FindingRiskResult(BaseModel):
    finding_id: str
    review_risk: str = Field(description="'lower', 'medium', 'higher', 'unknown'")
    risk_score: float | None = Field(default=None, description="0-100 deterministic score or None")
    risk_confidence: str = Field(description="'high', 'medium', 'low', 'unknown'")
    risk_assessment: RiskAssessment
    model_config = ConfigDict(extra="allow")

class RiskSummary(BaseModel):
    total_findings: int = 0
    assessed_findings: int = 0
    unassessed_findings: int = 0
    higher_risk_count: int = 0
    medium_risk_count: int = 0
    lower_risk_count: int = 0
    unknown_risk_count: int = 0
    average_risk_score: float | None = None
    model_config = ConfigDict(extra="allow")

class RiskAnalysisResult(BaseModel):
    analysis_id: str
    status: str = Field(default="success")
    enriched_findings: list[dict[str, Any]] = Field(default_factory=list)
    summary: RiskSummary = Field(default_factory=RiskSummary)
    model_config = ConfigDict(extra="allow")
```

---

## 4. Verification & Testing Strategy

- `test_risk_scorer.py`:
  - Verify mathematical factor calculations across F1–F6.
  - Verify boundary clamping ($0$ and $100$).
  - Verify threshold transitions: $29 \rightarrow \text{lower}$, $30 \rightarrow \text{medium}$, $59 \rightarrow \text{medium}$, $60 \rightarrow \text{higher}$.
  - Verify unmapped findings and unavailable graphs produce `review_risk == "unknown"` and `risk_score is None`.
- `test_risk_explainer.py`:
  - Verify mitigating observations are excluded when graph is incomplete or when zero tests are found.
  - Verify positive factors match observed evidence accurately.
  - Verify uncertainties list dynamic imports and truncation appropriately.
- `test_risk_analyzer.py`:
  - Verify non-mutating deep-copy of findings.
  - Verify summary counts and average score calculation.
  - Verify determinism across multiple runs with identical input.

