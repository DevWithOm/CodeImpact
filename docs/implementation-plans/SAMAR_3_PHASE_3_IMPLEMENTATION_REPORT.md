# SAMAR_3: Dependency & Impact Engine
## Phase 3: Dependency Graph Construction Implementation Report

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** PASS (All 56 Unit and Integration Tests Passing)  
**Project Root:** `C:\DeadCode`  
**Target Module:** `backend/app/services/dependency_impact/`  

---

## 1. Phase 3 Objective

Implement a complete, deterministic, and validated dependency graph construction engine that transforms Phase 2 Madge extraction outputs (`dependency_map` and `cycles`) into the canonical CodeImpact directed graph data structure. The engine computes node degrees, tags cycle members, calculates pre-truncation architectural statistics, and enforces deterministic visualization bounds without creating dangling edges.

---

## 2. Repository State Before Implementation

- Phase 2 Madge subprocess runner was completed, hardened, and verified with 35 passing tests.
- Target modules `cycle_detector.py` and `graph_builder.py` were 0-byte placeholders.
- Schema module `backend/app/schemas/graph.py` was a 0-byte placeholder.
- Fixture `backend/tests/fixtures/dependency_fixture/` contained verified TypeScript test files.

---

## 3. Existing Components Reused

1. `madge_runner.py`:
   - `run_madge()`: Subprocess coordinator producing valid dependency maps and circular dependency chains.
   - `normalize_repo_relative_path()`: Reused for consistent POSIX repository-relative path sanitization and directory traversal (`..`) rejection.
2. `fixtures/dependency_fixture/`: Used for real end-to-end integration tests without mocks.

---

## 4. Architecture & Module Responsibilities

```text
backend/app/services/dependency_impact/
├── madge_runner.py       # Raw tool execution (Madge CLI via Node.js, shell=False)
├── cycle_detector.py     # Cycle normalization, canonical rotation, and member tagging
├── graph_builder.py      # Directed graph construction, degree calculations, truncation, validation
└── __init__.py           # Unified export facade for SAMAR_3 interfaces
```

- **`cycle_detector.py`**:
  - `canonicalize_cycle_chain()`: Rotates circular dependency loops to begin with their lexicographically smallest element.
  - `normalize_cycles()`: Validates, deduplicates rotationally equivalent cycles, strips redundant return edges, and sorts chains deterministically.
  - `get_cycle_members()`: Extracts flat set of all file paths participating in any cycle.
  - `validate_cycles()`: Confirms all cycle edges exist in the dependency map.
- **`graph_builder.py`**:
  - `build_dependency_graph()`: Central graph construction engine.
  - `extract_finding_counts_by_file()`: Aggregates findings per file path.
  - `validate_graph_integrity()`: Validates degree identities and absence of dangling edges.
  - `create_graph_response()`: Envelopes graph and findings into top-level response schema.
- **`backend/app/schemas/graph.py`**:
  - Pydantic v2 data models: `GraphNode`, `GraphEdge`, `GraphStats`, `GraphData`, `DependencyGraphResponse`.

---

## 5. Input Contract

```python
def build_dependency_graph(
    dependency_map: dict[str, list[str]] | None,
    cycles: list[list[str]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    max_nodes: int = 150,
    max_edges: int = 200,
) -> dict[str, Any]:
    ...
```

- `dependency_map`: Dictionary mapping source module -> list of imported modules.
- `cycles`: Optional raw cycle list from Madge.
- `findings`: Optional static analysis finding dictionaries with `file_path`.
- `max_nodes`: Visualization node payload limit (default: 150).
- `max_edges`: Visualization edge payload limit (default: 200).

---

## 6. Path Normalization Strategy

- Reuses `normalize_repo_relative_path()` from Phase 2.
- Backslashes (`\`) converted to forward slashes (`/`).
- Leading `./` stripped.
- Path traversal sequences (`..`) rejected.
- Absolute paths (e.g. `C:/...` or `/...`) rejected.
- Result: Every node ID and edge endpoint is strictly a clean, repository-relative POSIX path.

---

## 7. Node Construction

- Node Universe: Automatically discovers every module that appears as a key in `dependency_map`, every module appearing in any import target list, and all cycle members.
- Node Schema:
  ```json
  {
    "id": "src/main.ts",
    "label": "main.ts",
    "file_path": "src/main.ts",
    "finding_count": 0,
    "cycle_member": false,
    "in_degree": 0,
    "out_degree": 1
  }
  ```
- `label`: Basename of the file (`Path(id).name`).
- `finding_count`: Aggregated dynamically from input findings.
- `cycle_member`: Boolean flag derived from cycle detection.

---

## 8. Directed Edge Construction

- **Fixed Edge Direction:** `SOURCE IMPORTS TARGET` (`source -> target`).
- **Edge Schema:**
  ```json
  {
    "id": "src/main.ts->src/app.ts",
    "source": "src/main.ts",
    "target": "src/app.ts",
    "relationship": "imports"
  }
  ```
- Duplicate dependencies are deduplicated so each directed relationship exists exactly once.
- Self-loops are filtered out.

---

## 9. Degree Calculation & Invariant Identities

- **In-Degree:** Number of direct importers (`target.in_degree += 1`).
- **Out-Degree:** Number of direct dependencies (`source.out_degree += 1`).
- **Mathematical Invariant:** Computed across the complete graph prior to truncation:
  $$\sum \text{in\_degree} == \text{edge\_count} == \sum \text{out\_degree}$$
- **Full-Graph Degree Preservation:** When visual truncation occurs, node objects retain their true complete-graph degree values.

---

## 10. Circular Dependency Normalization

- Discards cycles with fewer than 2 unique files.
- Canonicalizes rotational variants: `['user.ts', 'auth.ts']` and `['auth.ts', 'user.ts']` normalize to `['src/services/auth.ts', 'src/services/user.ts']`.
- Deduplicates identical cycles.
- Sorts cycles lexicographically.

---

## 11. Cycle-Member Identification

- Extracted as a flat set from normalized cycles.
- Tags every participating node with `cycle_member: true`.

---

## 12. Graph Statistics

Calculated prior to truncation to preserve architectural fidelity:

```json
{
  "node_count": 6,
  "edge_count": 5,
  "cycle_count": 1,
  "original_node_count": 6,
  "original_edge_count": 5,
  "returned_node_count": 6,
  "returned_edge_count": 5
}
```

- `node_count` & `original_node_count`: Complete unconstrained node count.
- `edge_count` & `original_edge_count`: Complete unconstrained edge count.
- `cycle_count`: Count of detected circular dependencies.
- `returned_node_count`: Number of nodes in `nodes` array.
- `returned_edge_count`: Number of edges in `edges` array.

---

## 13. Deterministic Truncation & Edge Integrity

When `node_count > max_nodes` or `edge_count > max_edges`:
1. Sets `truncated: true`.
2. Deterministic Node Ranking:
   - Rank 1: `finding_count` (descending)
   - Rank 2: `cycle_member` (`True` before `False`)
   - Rank 3: `in_degree` (descending: high-impact architectural hubs)
   - Rank 4: `file_path` (ascending: stable lexicographical tie-breaker)
3. Selects top `max_nodes`.
4. **Zero Dangling Edges:** Retains only edges where both `source` and `target` exist in the selected node set.
5. If edges still exceed `max_edges`, ranks edges by endpoint findings and cycle significance.
6. Complete cycle paths in `cycles` array remain intact regardless of node pruning.

---

## 14. Graph Integrity Validation

Implemented in `validate_graph_integrity()`:
- Asserts all node IDs equal their `file_path`.
- Asserts all degree counts and finding counts are non-negative.
- Asserts every edge has `relationship="imports"`.
- Asserts zero dangling edges.
- Validates returned counts match actual collection lengths.

---

## 15. Orchestrator Integration Status

- `build_dependency_graph` and `create_graph_response` are exported from `backend.app.services.dependency_impact`.
- Ready for one-line invocation in `backend/app/services/orchestrator.py` by TANUJA_4:
  ```python
  from backend.app.services.dependency_impact import build_dependency_graph, create_graph_response
  graph = build_dependency_graph(madge_result["dependency_map"], madge_result["cycles"], findings)
  ```

---

## 16. Test Results Summary

Ran `python -m pytest backend/tests/ -v`:

| Test Suite | File | Tests Run | Passed | Failed | Skipped |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Cycle Detector** | `backend/tests/test_cycle_detector.py` | 9 | 9 | 0 | 0 |
| **Graph Builder** | `backend/tests/test_graph_builder.py` | 12 | 12 | 0 | 0 |
| **Madge Runner (Regression)** | `backend/tests/test_madge.py` | 35 | 35 | 0 | 0 |
| **Total Backend** | **All suites combined** | **56** | **56** | **0** | **0** |

---

## 17. Fixture Integration Test Evidence

Executed `test_real_madge_fixture_integration`:
- Input: Real Madge 8.0.0 output from `backend/tests/fixtures/dependency_fixture/`.
- Produced:
  - 6 nodes: `app.ts`, `main.ts`, `auth.ts`, `user.ts`, `utils.ts`, `app.test.ts`.
  - 5 edges: `app.ts->utils.ts`, `main.ts->app.ts`, `auth.ts->user.ts`, `user.ts->auth.ts`, `app.test.ts->app.ts`.
  - 1 cycle: `['src/services/auth.ts', 'src/services/user.ts']`.
  - Degree checks: `sum(in_degree) == 5 == sum(out_degree) == len(edges)`.
  - Stats: `node_count=6`, `edge_count=5`, `cycle_count=1`, `truncated=False`.
  - Pydantic schema validation: 100% compliant with `DependencyGraphResponse`.

---

## 18. Files Created & Modified

### Created:
1. `backend/app/services/dependency_impact/cycle_detector.py`
2. `backend/app/schemas/graph.py`
3. `backend/tests/test_cycle_detector.py`
4. `backend/tests/test_graph_builder.py`
5. `docs/implementation-plans/SAMAR_3_PHASE_3_IMPLEMENTATION_PLAN.md`
6. `docs/implementation-plans/SAMAR_3_PHASE_3_IMPLEMENTATION_REPORT.md`

### Modified:
1. `backend/app/services/dependency_impact/graph_builder.py`
2. `backend/app/services/dependency_impact/__init__.py`

---

## 19. Remaining Limitations

- Runtime dynamic imports (`import(variable)`) are omitted by Madge upstream; the graph builder accurately reflects all statically observed dependencies.
- Truncation prioritizes finding-associated and cycle-associated files, which may fragment disconnected peripheral subgraphs when aggressive truncation limits (e.g. `< 10` nodes) are configured.

---

## 20. Final Completion Verdict

# **PASS**
Phase 3 (Dependency Graph Construction) is completely implemented, verified, and passing all 56 tests across the test suite. All graph invariants, truncation bounds, degree identities, and JSON schemas are locked and production-ready.

