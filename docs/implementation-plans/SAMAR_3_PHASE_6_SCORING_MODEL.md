# SAMAR_3 — PHASE 6 SCORING MODEL
## Deterministic Review-Risk Scoring Specification

**Author:** SAMAR_3 (Dependency & Impact Engine)  
**Date:** 2026-10-31  
**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Status:** Approved for Implementation  

---

## 1. Principles & Objectives

The Review-Risk Scoring Model is a deterministic, evidence-based algorithm designed to measure human review priority. It computes a bounded score between **0 and 100** based on observed structural dependencies, cyclic couplings, test relationships, entry-point indicators, and static analysis confidence.

### Core Invariants
1. **0–100 Bounded Scale**:
   $$\text{Total Risk Score} = \min\left(100, \max\left(0, \sum_{i=1}^{6} \text{Factor}_i\right)\right)$$
2. **Deterministic Reproducibility**: Identical inputs produce identical factor breakdowns, scores, confidence ratings, and explanations.
3. **Absence of Evidence is Not Evidence of Absence**:
   - Zero tests found contributes $0$ points to risk; it **never** subtracts points.
   - Missing or truncated graph data reduces **confidence**, not risk.
4. **Separation of Concerns**:
   - `risk_score`: Deterministic numerical metric of observed potential blast radius ($0–100$).
   - `review_risk`: Categorical priority (`lower`, `medium`, `higher`, `unknown`).
   - `risk_confidence`: Reliability/completeness of supporting evidence (`high`, `medium`, `low`, `unknown`).
   - `analysis_completeness`: Pipeline stage execution state (`complete`, `partial`, `unavailable`).

---

## 2. Factor Allocations & Formulas

The total score is comprised of six distinct, non-overlapping factors totaling 100 points maximum:

| Factor | Factor Name | Max Points | Primary Evidence Sources |
| :---: | :--- | :---: | :--- |
| **F1** | Dependency Exposure | 25 | `direct_dependants`, `summary.direct_dependant_count` |
| **F2** | Cycle Exposure | 15 | `cycle_member`, `cycles`, `self_dependency_detected` |
| **F3** | Entry-Point Exposure | 20 | `entry_points`, `file_path`, package manifest indicators |
| **F4** | Test-Impact Evidence | 15 | `test_impact.candidate_tests`, `test_impact.summary` |
| **F5** | Finding Evidence & Uncertainty | 15 | `category`, `evidence_class`, `source_tool` |
| **F6** | Special Structural Exposure | 10 | `direct_dependencies`, architectural layer heuristics |
| **Total** | | **100** | |

---

### Factor 1: Dependency Exposure (Max 25 pts)
Measures the blast radius of modifying a module based on how many other modules directly import it.
- **Base Formula**:
  $$\text{Base Score} = \min(20, \text{direct\_dependant\_count} \times 5)$$
  *(Each direct dependant contributes 5 points up to 20 points).*
- **Breadth Bonus (+5 pts)**:
  - If $\text{direct\_dependant\_count} \ge 5$, or if direct dependants span across $\ge 2$ distinct top-level directories, add $+5$ points (capped at 25).
- **Edge cases**:
  - Unmapped or graph unavailable: Observed value $0$, status `"unmapped"` or `"unavailable"`, contribution $0$, uncertainty flagged.

---

### Factor 2: Cycle Exposure (Max 15 pts)
Measures architectural entanglement where changing module $A$ propagates through circular import chains.
- **Multi-File Cycle**:
  - If $\text{cycle\_member} == \text{True}$ and at least one cycle chain contains $\ge 2$ unique files:
    $$\text{Score} = 15$$
- **Self-Loop Only**:
  - If $\text{self\_dependency\_detected} == \text{True}$ and not participating in a multi-file cycle:
    $$\text{Score} = 4$$
- **No Cycle Detected**:
  $$\text{Score} = 0$$
- **Unknown Cycle State** (Graph truncated/unavailable):
  $$\text{Score} = 0 \quad (\text{Confidence penalized, uncertainty recorded})$$

---

### Factor 3: Entry-Point Exposure (Max 20 pts)
Application entry points execute at runtime (e.g., via CLI, web server boot, or package import) and often have **zero** incoming static imports in the repository.
- **Strongly Supported Entry Point (20 pts)**:
  - File is registered in `package.json` (`main`, `module`, `bin`, `exports`), or explicitly verified as application entry.
- **Moderately Supported Entry Point (12 pts)**:
  - Standard top-level entry paths (e.g. `src/index.ts`, `src/main.ts`, `src/App.tsx`, `server.ts`).
- **Weak Heuristic Entry Point (5 pts)**:
  - Secondary entry pattern (e.g. `cli.ts`, `bootstrap.ts`, `bin/*.js`).
- **No Entry Point Identified (0 pts)**:
  $$\text{Score} = 0$$

---

### Factor 4: Test-Impact Evidence (Max 15 pts)
Indicates whether test code directly imports or transitively relies on the flagged source file, requiring test suite updates if refactored.
- **Direct Test Relationship (15 pts)**:
  - Identified test file directly imports the flagged module (`mapping_status == "direct"` or `direct_test_count > 0`).
- **Transitive Test Relationship (10 pts)**:
  - Identified candidate test connects via bounded dependency graph path (`evidence_type == "transitive_dependency"`).
- **Heuristic Test Relationship Only (6 pts)**:
  - Basename/proximity heuristic match without direct graph link (`mapping_status == "heuristic"`).
- **No Tests Identified (0 pts)**:
  $$\text{Score} = 0$$
  > **Safety Invariant**: Score of 0 adds zero points, but **never subtracts**. Absense of tests does not indicate code safety.

---

### Factor 5: Finding Evidence & Uncertainty (Max 15 pts)
Evaluates the static analysis finding category and classification confidence:
- **Category Impact**:
  - `unused_export`: Exported symbols could be consumed by external libraries, dynamic imports, or untyped consumers $\rightarrow +10$ pts.
  - `unused_file`: Module appears wholly unreferenced $\rightarrow +5$ pts.
  - `duplicate_code`: Refactoring duplicate code requires structural alignment $\rightarrow +8$ pts.
  - Other categories: $+5$ pts.
- **Inconclusive Tool Evidence**:
  - If `evidence_class == "inconclusive"` or `source_tool == "knip"` without secondary corroboration $\rightarrow +5$ pts (uncertainty premium).
- **Additive Formulation & Cap**:
  - Category base points and inconclusive evidence bonus are strictly additive, capped at $\min(15, \text{Base} + \text{Bonus})$.
  - Example: `unused_export` ($10$ pts) $+$ `inconclusive` ($5$ pts) $= 15$ pts.
  - Example: `unused_file` ($5$ pts) $+$ `inconclusive` ($5$ pts) $= 10$ pts.

---

### Factor 6: Special Structural Exposure (Max 10 pts)
Accounts for architectural position and high outgoing dependency coupling:
- **High Outgoing Dependencies**:
  - If $\text{direct\_dependency\_count} \ge 5 \rightarrow +5$ pts (complex orchestration hub).
- **Core Architecture Directory**:
  - File resides in critical paths (`services/`, `core/`, `api/`, `config/`, `shared/`) $\rightarrow +5$ pts.
- **Cap**: $\min(10, \text{Sum})$.

---

## 3. Classification Thresholds

| Score Range | Review Risk Category | Meaning |
| :---: | :---: | :--- |
| **0 – 29** | `lower` | Low observable blast radius in a verified complete analysis. Minimal dependants and tests. |
| **30 – 59** | `medium` | Moderate coupling, some dependants or candidate tests; standard refactoring review needed. |
| **60 – 100** | `higher` | High exposure; multiple dependants, cycles, entry points, or critical tests. Priority human inspection required. |
| **N/A** | `unknown` | Analysis could not be performed (unmapped finding, missing file, or unavailable graph). |

### Special Classification Rule for Incomplete Data
If `mapping_status != "mapped"` or `graph_status == "unavailable"`:
- `review_risk = "unknown"`
- `risk_score = None`
- `risk_confidence = "unknown"`
- `analysis_completeness = "unavailable"`

---

## 4. Confidence & Completeness Rules

### 4.1 Evidence Confidence (`risk_confidence`)
- **`high`**: Finding mapped, graph complete (`truncated == False`), test impact status `"success"`, entry points checked.
- **`medium`**: Finding mapped, graph complete, but test impact partial or heuristic only.
- **`low`**: Finding mapped, but graph truncated (`truncated == True`) or test impact unavailable.
- **`unknown`**: Finding unmapped or graph unavailable.

### 4.2 Analysis Completeness (`analysis_completeness`)
- **`complete`**: Graph status `"success"`, not truncated, test impact status `"success"`.
- **`partial`**: Graph status `"partial"` (truncated) or test impact status `"partial"`.
- **`unavailable`**: Graph status `"unavailable"` or finding unmapped.

---

## 5. Mitigations vs. Uncertainties

### Mitigating Observations (Strict Quality Filter)
Only genuine negative findings from a **complete** analysis qualify:
- "No incoming static import edges identified in complete dependency graph."
- "No circular dependencies detected for this module in complete graph."
- "No application entry-point characteristics identified."

*Prohibited as mitigations:*
- "No tests found" (this is an uncertainty, NOT a mitigation).
- "No dependants found in truncated graph" (this is incomplete data, NOT a mitigation).

### Uncertainties
Transparently cataloged for developer awareness:
- Static dependency graph excludes dynamic `import()` expressions and runtime reflection.
- Graph was truncated to fit visualization thresholds.
- Identified test candidates do not guarantee runtime code execution or assertion coverage.
- File may be loaded dynamically by framework runtime without static repository imports.

