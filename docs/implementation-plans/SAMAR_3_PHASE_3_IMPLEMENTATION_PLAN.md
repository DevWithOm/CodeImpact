# SAMAR_3: Dependency & Impact Engine
## Phase 3: Dependency Graph Construction Implementation Plan

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** READY FOR IMPLEMENTATION  
**Target Module:** `backend/app/services/dependency_impact/`  

---

## 1. Objective

Implement a high-performance, deterministic, and validated dependency graph construction engine that converts the Phase 2 Madge extraction output (`dependency_map` and `cycles`) into a structured directed graph. The engine calculates node degrees (`in_degree`, `out_degree`), tracks cycle membership, computes pre-truncation architectural statistics, and enforces deterministic bounded visualization truncation without dangling edges.

---

## 2. Current Repository State & Reusable Components

- **`madge_runner.py`**:
  - `run_madge(repo_path)`: Returns structured `{status, dependency_map, cycles, error, warnings, metadata}`.
  - `normalize_repo_relative_path(path_str)`: Sanitizes and normalizes paths to repository-relative POSIX forward slashes, rejecting traversal (`..`) and absolute paths.
- **`backend/tests/fixtures/dependency_fixture/`**:
  - TypeScript fixture with 6 files, 5 dependency edges, and 1 cycle (`auth.ts` <-> `user.ts`).
- **Target Placeholders to Implement**:
  - `backend/app/services/dependency_impact/cycle_detector.py`
  - `backend/app/services/dependency_impact/graph_builder.py`
  - `backend/app/schemas/graph.py` (Pydantic models for validation and typing)
  - `backend/tests/test_cycle_detector.py`
  - `backend/tests/test_graph_builder.py`

---

## 3. Data Contracts & Invariants

### 3.1 Input Contract
- `dependency_map`: `dict[str, list[str]]` (mapping from source module to list of imported modules).
- `cycles`: `list[list[str]] | None` (list of cycle chains from Madge or external detection).
- `findings`: `list[dict] | None` (optional normalized static analysis findings with `file_path`).
- `max_nodes`: `int` (default 150).
- `max_edges`: `int` (default 200).

### 3.2 Canonical Output Contract
```json
{
  "nodes": [
    {
      "id": "src/main.ts",
      "label": "main.ts",
      "file_path": "src/main.ts",
      "finding_count": 0,
      "cycle_member": false,
      "in_degree": 0,
      "out_degree": 1
    }
  ],
  "edges": [
    {
      "id": "src/main.ts->src/app.ts",
      "source": "src/main.ts",
      "target": "src/app.ts",
      "relationship": "imports"
    }
  ],
  "cycles": [
    ["src/services/auth.ts", "src/services/user.ts"]
  ],
  "stats": {
    "node_count": 6,
    "edge_count": 5,
    "cycle_count": 1,
    "original_node_count": 6,
    "original_edge_count": 5,
    "returned_node_count": 6,
    "returned_edge_count": 5
  },
  "truncated": false
}
```

### 3.3 Core Graph Invariants
1. **Edge Direction:** `SOURCE IMPORTS TARGET` (`source -> target`).
2. **Degree Identity (Full Graph):** `sum(in_degree) == edge_count == sum(out_degree)`.
3. **No Dangling Edges:** Every edge in `edges` satisfies `edge["source"] in node_ids` and `edge["target"] in node_ids`.
4. **Deterministic Ordering:** Nodes sorted by `id`, edges sorted by `id` (`source->target`).
5. **Cycle Preservation:** Full cycle chains are preserved in `cycles` even if visual nodes are truncated.

---

## 4. Truncation Strategy

When `node_count > max_nodes` or `edge_count > max_edges`:
1. Calculate full graph statistics before truncation (`original_node_count`, `original_edge_count`, `cycle_count`).
2. Rank nodes deterministically:
   - Priority 1: `finding_count` (descending)
   - Priority 2: `cycle_member` (descending: `True` before `False`)
   - Priority 3: `in_degree` (descending: architectural hubs)
   - Priority 4: `file_path` (ascending: lexicographical tie-breaker)
3. Select top `max_nodes`.
4. Filter edges so both `source` and `target` exist in the selected node set.
5. If remaining edges still exceed `max_edges`, retain top `max_edges` with deterministic endpoint sorting.
6. Node degrees retain their original full-graph values.

---

## 5. Implementation Roadmap
1. `cycle_detector.py`: Cycle normalization, canonical representation, deduplication, cycle member extraction.
2. `schemas/graph.py`: Pydantic models for `GraphNode`, `GraphEdge`, `GraphStats`, `GraphData`.
3. `graph_builder.py`: Node universe construction, degree computation, finding counts, truncation, serialization.
4. `test_cycle_detector.py`: Tests for empty, simple, multi-node, shifted, and invalid cycles.
5. `test_graph_builder.py`: Tests for nodes, edges, degrees, statistics, truncation, and real Madge fixture integration.
6. Full regression verification: Run all 35 Phase 2 tests and new Phase 3 tests.
7. Final report: `SAMAR_3_PHASE_3_IMPLEMENTATION_REPORT.md`.

