# SAMAR_3: Dependency & Impact Engine
## Phase 4: Finding-Level Impact Analysis Implementation Plan

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** READY FOR IMPLEMENTATION  

---

## 1. Objective

Connect static analysis findings from OM_2 to the Phase 3 dependency graph to determine the direct impact of flagged files. Answer:
1. Which graph node corresponds to each finding?
2. Which files directly import/depend on that flagged file (direct dependants)?
3. Which files does the flagged file directly import (direct dependencies)?
4. What exact graph edge serves as static evidence for each relationship?
5. How are self-loops, cycles, unmapped findings, and invalid paths reliably handled?

---

## 2. Invariants & Scope Boundaries

- **Edge Direction**: `SOURCE IMPORTS TARGET` (`A -> B` means `A` imports `B`).
  - Direct dependants of `B` are sources of incoming edges (`A`).
  - Direct dependencies of `A` are targets of outgoing edges (`B`).
- **Strictly Non-Transitive**: Transitive dependants (e.g. `main -> app -> utils` means `main` is NOT a direct dependant of `utils`) are excluded.
- **Self-Loops (`A -> A`)**: Preserved in graph topology, but excluded from external `direct_dependants` and flagged as `self_dependency_detected = True`.
- **Evidence Backing**: Every direct dependant and dependency must reference the canonical edge ID, source, target, relationship, and evidence type (`static_import_relationship`).
- **No Side Effects**: Pure analysis functions. No subprocesses run against repo files, no network requests, no code modifications, no risk scoring or test mapping.

---

## 3. Architecture & Module Design

### 3.1 Pydantic Schemas (`backend/app/schemas/impact.py`)
- `ImpactEvidence`:
  - `edge_id`: str (`"source->target"`)
  - `source`: str
  - `target`: str
  - `relationship`: str (`"imports"`)
  - `evidence_type`: str (`"static_import_relationship"`)
- `DirectDependant` / `DirectDependencyItem`:
  - `file_path`: str
  - `relationship`: str (`"imports"`)
  - `evidence`: `ImpactEvidence`
- `FindingImpactSummary`:
  - `direct_dependant_count`: int
  - `direct_dependency_count`: int
- `EnrichedFinding` / `FindingImpact`:
  - `finding_id`: str | None
  - `file_path`: str | None
  - `category` / `finding_type`: str | None
  - `mapping_status`: str (`"mapped"`, `"unmapped"`, `"invalid_path"`, `"missing_file_path"`)
  - `impact_status`: str (`"success"`, `"partial"`, `"unavailable"`)
  - `direct_dependants`: list[`DirectDependant`]
  - `direct_dependencies`: list[`DirectDependant`]
  - `self_dependency_detected`: bool
  - `cycle_member`: bool
  - `cycles`: list[list[str]]
  - `summary`: `FindingImpactSummary`
  - Preservation of all original fields (`evidence`, `risk_factors`, `metadata`, `start_line`, etc.).

### 3.2 Finding Mapper (`backend/app/services/dependency_impact/finding_mapper.py`)
- `normalize_finding_path(path: str | None) -> tuple[str | None, str]`:
  Validates path, checks for missing/None/empty, invalid absolute paths, traversal `..`.
- `map_finding_to_node(finding: dict[str, Any], node_ids: set[str]) -> tuple[dict[str, Any], str, str | None]`:
  Returns normalized finding adapter, `mapping_status`, and matched `node_id`.
- `map_findings_to_nodes(findings: list[dict[str, Any]], graph_nodes: list[dict[str, Any]] | set[str]) -> list[tuple[dict[str, Any], str, str | None]]`.

### 3.3 Impact Analyzer (`backend/app/services/dependency_impact/impact_analyzer.py`)
- `build_graph_indexes(edges: list[dict[str, Any]]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]`:
  Builds `incoming_edges` (keyed by target) and `outgoing_edges` (keyed by source) in $O(E)$ time.
- `extract_direct_dependants(node_id: str, incoming_edges: dict[str, list[dict]]) -> tuple[list[dict], bool]`:
  Finds unique importers of `node_id`, excluding self-loops. Detects self-loops.
- `extract_direct_dependencies(node_id: str, outgoing_edges: dict[str, list[dict]]) -> list[dict]`:
  Finds unique imported modules from `node_id`, excluding self-loops.
- `analyze_finding_impact(...) -> dict[str, Any]`:
  Enriches an individual finding.
- `analyze_impact(graph: dict[str, Any] | BaseModel, findings: list[dict[str, Any]], analysis_id: str = "") -> dict[str, Any]`:
  Coordinates the full enrichment pipeline, returning `{ "analysis_id": ..., "graph": ..., "enriched_findings": [...] }`.

---

## 4. Test Strategy

1. `backend/tests/test_finding_mapper.py`:
   - Exact path match.
   - Windows backslash separator normalization (`src\utils.ts` -> `src/utils.ts`).
   - Redundant `./` prefix (`./src/utils.ts` -> `src/utils.ts`).
   - Missing/None/empty file paths (`missing_file_path`).
   - Traversal attempt (`../secret.ts` -> `invalid_path`).
   - Absolute host path (`C:\DeadCode\app.ts` or `/etc/passwd` -> `invalid_path`).
   - Finding path not in graph (`unmapped`).
   - Multiple findings mapped to the same file without collision or mutation.
   - Preservation of original finding fields.
2. `backend/tests/test_impact_analyzer.py`:
   - Single direct dependant (`A -> B`, finding on `B` returns `A`).
   - Multiple direct dependants (`A -> B`, `C -> B`, finding on `B` returns `[A, C]`).
   - No direct dependants (finding on root importer `A` returns `[]`).
   - Exclusion of transitive dependants (`main -> app -> utils`, finding on `utils` returns `app`, never `main`).
   - Direct dependencies (`app -> utils`, finding on `app` returns `utils`).
   - Self-loop (`A -> A`: `self_dependency_detected = True`, `A` not in external dependants).
   - Cycle member node (`A -> B -> A`: `cycle_member = True`, `cycles` populated).
   - Complete evidence verification (`edge_id`, `source`, `target`, `relationship`, `evidence_type`).
   - Synthetic fixture end-to-end integration test (`FIND-001`, `FIND-002`, `FIND-003`).
   - Error & edge conditions: empty graph, empty findings, malformed edges, unmapped findings.

---

## 5. Verification & Regression Plan

- Run `python -m pytest backend/tests/test_finding_mapper.py -v`.
- Run `python -m pytest backend/tests/test_impact_analyzer.py -v`.
- Run full suite `python -m pytest backend/tests/ -v` (expecting ~95+ passing tests across all test suites).

