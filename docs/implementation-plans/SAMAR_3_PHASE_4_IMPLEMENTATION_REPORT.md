# SAMAR_3: Dependency & Impact Engine
## Phase 4: Finding-Level Impact Analysis Implementation Report

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (All Acceptance Criteria Met)  

---

## 1. Objective

The objective of Phase 4 is to connect static analysis findings from **OM_2** to the dependency graph built in Phase 3 by **SAMAR_3**, enabling finding-level impact analysis. Specifically, the engine determines:
1. Which graph node corresponds to each finding via safe path normalization.
2. Which files directly import/depend on that flagged file (direct dependants via incoming edges).
3. Which files are directly imported by that flagged file (direct dependencies via outgoing edges).
4. Full evidence traceability connecting each relationship directly to a Phase 3 directed edge.
5. Robust handling for self-loops, circular dependency contexts, unmapped findings, and invalid paths.

---

## 2. Existing Files Inspected

- `backend/app/services/dependency_impact/madge_runner.py`: Path normalization and subprocess integration.
- `backend/app/services/dependency_impact/cycle_detector.py`: Cycle normalization, canonicalization, and membership sets.
- `backend/app/services/dependency_impact/graph_builder.py`: Directed graph builder with bounded truncation, self-loop preservation, and integrity validation.
- `backend/app/schemas/graph.py`: Phase 3 Pydantic schemas (`GraphNode`, `GraphEdge`, `GraphStats`, `GraphData`, `DependencyGraphResponse`).
- `docs/implementation-plans/OM_2.md`: Normalized finding schema specification (§5.3–5.5).
- `docs/implementation-plans/SAMAR_3_PHASE_1_INTEGRATION_CONTRACT.md`: Phase 1 baseline integration contract.
- `backend/app/services/orchestrator.py`: Orchestrator interface inspection.

---

## 3. Finding Schema Discovered & Adapted

Inspection confirmed the OM_2 normalized finding schema:
- `finding_id`: Unique stable identifier (e.g. `"f_001"`).
- `file_path`: Repository-relative POSIX path (e.g. `"src/utils/helpers.ts"`).
- `category`: Finding category (`"unused_export"`, `"unused_file"`, `"duplicate_code"`, etc.).
- `start_line` / `end_line`: Integer line numbers or `null`.
- `symbol`: Name of unreferenced export or `null`.
- `source_tool`: Tool producing the observation (`"knip"`, `"jscpd"`).
- `description`: Neutral observation text.
- `evidence`: List of static analysis evidence dictionaries.
- `risk_factors`: Array of risk factor strings.
- `metadata`: Tool-specific details.

**Adapter Strategy:**
`finding_mapper.py` implements `extract_finding_adapter`, supporting both OM_2's canonical schema and alternate field aliases (`id` for `finding_id`, `type` or `finding_type` for `category`, `message` for `description`). All original fields are strictly preserved without in-place mutation.

---

## 4. Graph Contract Reused

The engine directly consumes the Phase 3 directed graph contract:
- **Canonical Edge Direction**: `SOURCE IMPORTS TARGET` (`source -> target`).
  - An edge `src/main.ts -> src/app.ts` indicates that `src/main.ts` imports `src/app.ts`.
  - For a finding on `src/app.ts`, `src/main.ts` is an incoming edge source, hence a **direct dependant**.
  - For a finding on `src/main.ts`, `src/app.ts` is an outgoing edge target, hence a **direct dependency**.
- **Nodes**: Repository-relative POSIX identifiers (`node.id == node.file_path`).
- **Edges**: Deterministic ID formatted as `"{source}->{target}"` with `relationship: "imports"`.
- **Cycles**: Preserved normalized cycles list `[["src/auth.ts", "src/user.ts"]]`.

---

## 5. New Modules Created

1. `backend/app/schemas/impact.py`:
   - `ImpactEvidence`: Canonical edge ID, source, target, relationship, and evidence type (`"static_import_relationship"`).
   - `DirectDependant`: Dependent/dependency file item containing `file_path`, `relationship`, and `evidence`.
   - `FindingImpactSummary`: Direct dependant count and direct dependency count.
   - `EnrichedFinding`: Complete Pydantic v2 model combining finding data, mapping status, impact status, and direct impact relationships.
2. `backend/app/services/dependency_impact/finding_mapper.py`:
   - `validate_and_normalize_path`: Safe path normalization with directory traversal (`..`) and absolute path rejection.
   - `extract_finding_adapter`: Multi-schema finding adapter preserving all original attributes.
   - `map_finding_to_node`: Maps individual findings to graph node IDs.
   - `map_findings_to_nodes`: Batch mapping preserving multiple findings on the same file without merging.
3. `backend/app/services/dependency_impact/impact_analyzer.py`:
   - `build_graph_indexes`: $O(V + E)$ incoming and outgoing edge indexes.
   - `extract_direct_dependants`: Extracts unique direct dependants, excludes self-loops, detects self-dependencies.
   - `extract_direct_dependencies`: Extracts unique direct dependencies, excludes self-loops.
   - `enrich_finding`: Integrates impact context, cycles, and evidence into finding dictionary.
   - `analyze_impact`: Top-level facade supporting both graph dictionary/schema and repository path workflows.
4. `docs/implementation-plans/SAMAR_3_PHASE_4_CONTRACT_AUDIT.md`:
   - Comprehensive audit of input contracts, directionality, and mapping rules.
5. `docs/implementation-plans/SAMAR_3_PHASE_4_IMPLEMENTATION_PLAN.md`:
   - Subphase-by-subphase implementation blueprint.
6. `backend/tests/test_finding_mapper.py`:
   - 15 unit tests covering normalization, traversal rejection, absolute paths, and multi-finding mappings.
7. `backend/tests/test_impact_analyzer.py`:
   - 13 unit and integration tests covering direct dependants, direct dependencies, self-loops, cycles, evidence, and synthetic/real fixture scenarios.

---

## 6. Existing Modules Modified

1. `backend/app/services/dependency_impact/__init__.py`:
   - Exported Phase 4 functions (`analyze_impact`, `build_graph_indexes`, `extract_direct_dependants`, `extract_direct_dependencies`, `enrich_finding`, `map_findings_to_nodes`, `map_finding_to_node`, `validate_and_normalize_path`, `extract_finding_adapter`) and impact schemas.
2. `backend/app/schemas/finding.py`:
   - Populated previously 0-byte file with `Finding`, `FindingEvidenceItem`, and re-exports of impact schemas.
3. `backend/app/schemas/__init__.py`:
   - Populated previously 0-byte file with central exports for graph and finding schemas.

---

## 7. Finding Normalization & Node Mapping Implementation

- **Path Normalization**: Uses `normalize_repo_relative_path` to guarantee POSIX separators (`/`), trim `./`, and reject directory traversal (`..`) or absolute paths (`C:\...`, `/...`).
- **Mapping Statuses**:
  - `mapped`: File matches a node in the dependency graph.
  - `unmapped`: File is valid but absent from the dependency graph.
  - `missing_file_path`: Finding lacks a `file_path` field.
  - `invalid_path`: Path is unsafe or malformed.
- **Independence**: Multiple findings on the same file are mapped independently, ensuring no findings are merged or lost.

---

## 8. Direct Dependant & Dependency Algorithms

### 8.1 Indexing
Before processing findings, directed edges are indexed in $O(E)$ time:
- `incoming_edges`: `dict[target, list[edge]]`
- `outgoing_edges`: `dict[source, list[edge]]`

### 8.2 Direct Dependants
For finding on node `B`:
- Read `incoming_edges.get(B, [])`.
- Each edge `A -> B` where `A != B` yields a direct dependant `A`.
- Transitive dependants (e.g. `main -> app -> B`) are excluded because `main` is not an incoming edge to `B`.
- Deduplication ensures each unique importing module is returned once.

### 8.3 Direct Dependencies
For finding on node `A`:
- Read `outgoing_edges.get(A, [])`.
- Each edge `A -> B` where `A != B` yields a direct dependency `B`.

### 8.4 Concrete Example
Given edges:
```text
src/main.ts -> src/app.ts
src/app.ts  -> src/utils.ts
src/admin.ts -> src/utils.ts
```
For finding on `src/utils.ts`:
- Incoming edges to `src/utils.ts`: `src/app.ts -> src/utils.ts` and `src/admin.ts -> src/utils.ts`.
- Direct dependants: `["src/admin.ts", "src/app.ts"]`.
- `src/main.ts` is an incoming edge to `src/app.ts`, not `src/utils.ts`, so it is excluded.

---

## 9. Self-Loop and Cycle Handling

- **Self-Loops (`A -> A`)**:
  - Detected during incoming/outgoing edge inspection.
  - Sets `self_dependency_detected = True`.
  - Node `A` is excluded from external direct dependants and direct dependencies.
- **Cycles**:
  - Cycles containing the mapped file path are extracted from `graph["cycles"]`.
  - Sets `cycle_member = True` and includes the cycle chains in `cycles`.
  - Cycle members are not transitively expanded into fake direct dependants.

---

## 10. Evidence Generation & Traceability

Every returned direct dependant and direct dependency includes a verified `evidence` block:
```json
{
  "edge_id": "src/app.ts->src/utils.ts",
  "source": "src/app.ts",
  "target": "src/utils.ts",
  "relationship": "imports",
  "evidence_type": "static_import_relationship"
}
```
No fabricated line numbers, unobserved call chains, or runtime failure claims are produced.

---

## 11. Status Handling

- **`success`**: Finding mapped to a graph node and impact computed against a complete graph.
- **`partial`**: Finding is unmapped (file not in graph), specifies an invalid path, or graph was truncated/partial. Explicit reasons are provided under `impact_reason`.
- **`unavailable`**: Graph was missing or empty.

---

## 12. Orchestrator Integration Status

- **Status**: Pure, decoupled service implemented and exported.
- **Callable via**:
  ```python
  from backend.app.services.dependency_impact import analyze_impact
  result = analyze_impact(graph, findings, analysis_id)
  ```
- Ready for clean integration by **TANUJA_4** in `backend/app/services/orchestrator.py` without modifying orchestration code.

---

## 13. Test Results

All 96 backend tests passed:

| Test Suite | Total | Passed | Failed | Skipped | Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `test_madge.py` (Phase 2 Runner & Windows Subprocess) | 35 | 35 | 0 | 0 | 8.2s |
| `test_cycle_detector.py` (Phase 3 Cycle Extraction) | 9 | 9 | 0 | 0 | 0.1s |
| `test_graph_builder.py` (Phase 3 Graph Construction & Integrity) | 24 | 24 | 0 | 0 | 0.4s |
| `test_finding_mapper.py` (Phase 4 Path Normalization & Node Mapping) | 15 | 15 | 0 | 0 | 0.2s |
| `test_impact_analyzer.py` (Phase 4 Impact Analysis & Evidence) | 13 | 13 | 0 | 0 | 1.7s |
| **Total Backend Test Suite** | **96** | **96** | **0** | **0** | **11.8s** |

---

## 14. Remaining Limitations

1. **Static Granularity**: Dependency edges represent file-to-file imports extracted by Madge. Specific symbol-to-symbol import references (e.g. which specific named function was imported) depend on AST-level symbol resolution, which is not provided by Madge.
2. **Framework Entry Points**: Entry-point detection and test candidate mapping are scheduled for Phase 5.
3. **Risk Scoring**: Risk categories (`lower`, `medium`, `higher`) remain uncalculated until Phase 6.

---

## 15. Final Verdict

**PASS** — Core implementation, evidence traceability, edge direction invariants, error and status handling, and 96/96 regression tests are fully passing.

