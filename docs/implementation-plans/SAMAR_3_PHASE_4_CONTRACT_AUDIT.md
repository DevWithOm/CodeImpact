# SAMAR_3: Dependency & Impact Engine
## Phase 4: Contract Audit & Integration Discovery Document

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (Contract Locked for Phase 4)  

---

## 1. Executive Summary

Phase 4 bridges the static analysis findings produced by **OM_2** with the dependency graph constructed by **SAMAR_3** in Phase 3. The goal is to provide **finding-level impact analysis** without overstepping into risk scoring (Phase 6), test mapping (Phase 5), or code modification.

This contract audit establishes:
1. The exact schema of findings provided as input.
2. The exact schema of the dependency graph consumed as input.
3. The adapter layer to handle property name variations (`finding_id` vs `id`, `category` vs `type`).
4. The edge direction and graph invariant contract.
5. The output enrichment structure and evidence model.

---

## 2. Input Contracts Inspected

### 2.1 Static Analysis Findings (from OM_2 & Phase 1 Contract)

Inspection of `docs/implementation-plans/OM_2.md` (§5.3–5.5) and `docs/implementation-plans/SAMAR_3_PHASE_1_INTEGRATION_CONTRACT.md` reveals the canonical finding structure:

```json
{
  "finding_id": "f_001",
  "category": "unused_export",
  "title": "Potentially unused export",
  "file_path": "src/utils/helpers.ts",
  "start_line": 12,
  "end_line": 18,
  "symbol": "formatDate",
  "source_tool": "knip",
  "description": "No static reference was found by the configured scan.",
  "evidence_class": "inconclusive",
  "review_risk": "unknown",
  "evidence": [
    {
      "kind": "static_reference_scan",
      "status": "not_found",
      "source": "knip",
      "details": "No direct static reference was returned by this configured scan."
    }
  ],
  "risk_factors": [],
  "metadata": {}
}
```

#### Field Compatibility & Adapter Rules:
To guarantee robustness across different components and test fixtures:
- **Identifier**: Primary key is `finding_id`; fallback to `id` if `finding_id` is absent.
- **File Path**: Required `file_path`. Must be a repo-relative POSIX path.
- **Finding Type**: Primary key is `category`; fallback to `type` or `finding_type`.
- **Message**: Primary key is `description`; fallback to `message` or `title`.
- **Preservation Rule**: All original keys and nested structures (`metadata`, `evidence`, `risk_factors`) are strictly preserved during enrichment.

### 2.2 Dependency Graph Contract (from SAMAR_3 Phase 3)

The Phase 3 dependency graph schema locked in `backend/app/schemas/graph.py` provides:
- **Nodes (`GraphNode`)**:
  - `id`: Unique repo-relative POSIX path (e.g., `"src/utils/helpers.ts"`).
  - `label`: Display basename (e.g., `"helpers.ts"`).
  - `file_path`: Canonical repo-relative POSIX path.
  - `finding_count`: Non-negative integer.
  - `cycle_member`: Boolean flag.
  - `in_degree`: Importer / dependant count.
  - `out_degree`: Imported dependency count.
- **Edges (`GraphEdge`)**:
  - `id`: Canonical ID formatted as `"{source}->{target}"`.
  - `source`: Importing module (importer).
  - `target`: Imported module (dependency).
  - `relationship`: Canonical string `"imports"`.
- **Cycles (`cycles`)**:
  - List of normalized cyclic path lists (e.g., `[["src/a.ts", "src/b.ts"]]`).

---

## 3. Directionality Invariant: SOURCE IMPORTS TARGET

```text
       source ---------------> target
   (importing module)      (imported module)
```

- When evaluating a finding on module `X`:
  - **Direct Dependants**: Any node `Y` where there is a directed edge `Y -> X` (`edge.target == X`). `Y` is directly importing `X`.
  - **Direct Dependencies**: Any node `Z` where there is a directed edge `X -> Z` (`edge.source == X`). `X` is directly importing `Z`.
  - **Transitive Exclusion**: If `W -> Y -> X`, `W` is a transitive dependant of `X`. Phase 4 strictly excludes `W` from the direct dependants of `X`.

---

## 4. Path Normalization Contract

All finding file paths must be normalized using `normalize_repo_relative_path` (from `madge_runner.py`):
1. Convert Windows backslashes `\` to `/`.
2. Strip leading `./` or trailing `/`.
3. Reject path traversal attempts containing `..`.
4. Reject absolute host paths (e.g. `C:\...` or `/var/...`).
5. Return empty/None on unresolvable or dangerous paths.

---

## 5. Mapping Statuses & Impact Statuses

### Mapping Status:
- `"mapped"`: Finding's file path matches a node in the graph.
- `"unmapped"`: Finding's file path is valid syntax but not present as a node in the graph.
- `"missing_file_path"`: Finding lacks a `file_path` field or it is null/empty.
- `"invalid_path"`: Finding contains an illegal path (absolute path or `..` traversal).

### Impact Status:
- `"success"`: Finding mapped successfully, graph is valid, direct impact computed.
- `"partial"`: Finding is unmapped (file not in graph), graph was truncated/partial, or mapping failed.
- `"unavailable"`: Graph data is missing, empty, or unparseable.

---

## 6. Output Contract: Enriched Findings

The enriched finding model integrates the impact information while preserving original fields:

```json
{
  "finding_id": "f_001",
  "file_path": "src/utils.ts",
  "category": "unused_export",
  "mapping_status": "mapped",
  "impact_status": "success",
  "direct_dependants": [
    {
      "file_path": "src/app.ts",
      "relationship": "imports",
      "evidence": {
        "edge_id": "src/app.ts->src/utils.ts",
        "source": "src/app.ts",
        "target": "src/utils.ts",
        "relationship": "imports",
        "evidence_type": "static_import_relationship"
      }
    }
  ],
  "direct_dependencies": [
    {
      "file_path": "src/helpers.ts",
      "relationship": "imports",
      "evidence": {
        "edge_id": "src/utils.ts->src/helpers.ts",
        "source": "src/utils.ts",
        "target": "src/helpers.ts",
        "relationship": "imports",
        "evidence_type": "static_import_relationship"
      }
    }
  ],
  "self_dependency_detected": false,
  "cycle_member": false,
  "cycles": [],
  "summary": {
    "direct_dependant_count": 1,
    "direct_dependency_count": 1
  }
}
```

---

## 7. Planned Component Division

1. `backend/app/schemas/impact.py`:
   Pydantic v2 schemas for `ImpactEvidence`, `DirectDependant`, `FindingImpactSummary`, and `EnrichedFinding`.
2. `backend/app/services/dependency_impact/finding_mapper.py`:
   Functions to normalize finding paths, validate, and map findings to graph nodes.
3. `backend/app/services/dependency_impact/impact_analyzer.py`:
   Indexed graph lookup (`incoming_edges`, `outgoing_edges`), direct dependant/dependency calculation, self-loop and cycle handling, evidence generation, and top-level `analyze_impact`.
4. `backend/app/services/dependency_impact/__init__.py`:
   Public re-exports of schemas and analysis functions.
5. `backend/tests/test_finding_mapper.py` & `backend/tests/test_impact_analyzer.py`:
   Full test coverage adhering to acceptance criteria.

