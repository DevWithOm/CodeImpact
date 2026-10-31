# SAMAR_3: Dependency & Impact Engine
## Phase 4: Integration Audit Document

**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Author:** SAMAR_3 (Dependency & Impact Engine Architect)  
**Status:** COMPLETE (Audit Completed, Hardening Opportunities Identified)  

---

## 1. Executive Summary

This integration audit reviews the Phase 4 implementation against four critical integration considerations before making targeted hardening changes:
1. **Graph completeness and truncation propagation**: How truncation flags and upstream completeness affect impact statuses.
2. **Empty graph vs unavailable graph**: Ensuring valid empty graphs (analyzed codebases with no imports) are distinguished from failures (missing Madge, process crashes, unparseable outputs).
3. **Prevention of duplicate Madge execution**: Ensuring that when an orchestrator builds the graph, the impact analyzer never re-invokes Madge.
4. **Preservation of original finding data**: Ensuring original static analysis fields (symbols, line numbers, knip evidence, metadata) are preserved unmutated and serialized faithfully.

---

## 2. Code Inspection & Audit Findings

### 2.1 Task A: Graph Completeness & Truncation Propagation

#### Existing Code Behavior:
In `backend/app/services/dependency_impact/impact_analyzer.py` (`enrich_finding`):
```python
        # Status: success (or partial if graph was truncated)
        result["impact_status"] = IMPACT_STATUS_SUCCESS
        if graph_is_truncated:
            result["impact_note"] = "Graph was truncated for visualization; degrees reflect full graph"
```

#### Confirmed Issue:
When `graph_is_truncated` is `True`, `impact_status` remained `IMPACT_STATUS_SUCCESS` with an `impact_note`, rather than setting `impact_status = IMPACT_STATUS_PARTIAL`.
Per integration requirements:
- A complete graph produces `impact_status = "success"`.
- A truncated graph must produce `impact_status = "partial"`.
- A graph with partial upstream analysis (`status == "partial"`) must produce `impact_status = "partial"`.
- A graph with unavailable analysis (`status == "unavailable"`) must produce `impact_status = "unavailable"`.

#### Remediation Plan:
Update `enrich_finding` and `analyze_impact` so that when `graph_is_truncated` is True or the upstream graph's status is `"partial"`, mapped findings receive `impact_status = IMPACT_STATUS_PARTIAL` with a clear explanation in `impact_reason` / `impact_note`.

---

### 2.2 Task B: Empty Graph vs. Unavailable Graph

#### Existing Code Behavior:
In `backend/app/services/dependency_impact/impact_analyzer.py` (`analyze_impact`):
```python
    else:
        graph_dict = _extract_graph_dict(graph_or_repo)
        if not graph_dict or not (graph_dict.get("nodes") or graph_dict.get("edges")):
            # Empty graph or None
            if not graph_dict:
                graph_is_available = False
        graph_is_truncated = bool(graph_dict.get("truncated", False))
```

#### Confirmed Issue:
1. If `graph_input` is `None`, `_extract_graph_dict` returns `{}` and sets `graph_is_available = False`.
2. However, if `graph_input` is an error dictionary, e.g. `{"status": "unavailable", "error": {"code": "MADGE_NOT_FOUND"}}`, `graph_dict` is truthy, but `nodes` and `edges` are absent. The code defaulted `graph_is_available = True`, causing findings to be marked `mapping_status = "unmapped"` and `impact_status = "partial"` ("file not present in graph"), rather than recognizing the graph as **unavailable** (`impact_status = "unavailable"`).
3. Conversely, a valid empty graph from a successful scan (e.g. `{"nodes": [], "edges": [], "cycles": [], "stats": {...}, "truncated": false}`) was not explicitly validated against `status == "unavailable"` or `status == "failed"`.

#### Remediation Plan:
Implement explicit status and structure detection:
- Check `graph_dict.get("status")`: If `"unavailable"` or `"failed"`, or if `graph_dict` is `None` / empty dict without graph keys, flag `graph_is_available = False`.
- If `graph_dict` is a valid empty graph (`nodes == []`, `edges == []`, `stats` present, status not `"unavailable"` or `"failed"`), flag `graph_is_available = True`, `graph_is_truncated = False`, and let impact analysis proceed normally.

---

### 2.3 Task C: Duplicate Madge Execution Prevention

#### Existing Code Behavior:
`analyze_impact` accepts `graph_or_repo: Any`. If `isinstance(graph_or_repo, str)`, it executes:
```python
dep_result = get_dependency_map(repo_path)
circ_result = get_circular_dependencies(repo_path)
```
If `graph_or_repo` is a dictionary or Pydantic model, it does not call Madge.

#### Confirmed Issue & Risk:
If an orchestrator already invokes Madge and passes a pre-built graph, Madge is not called. However:
1. The parameter was named `graph_or_repo`, which could be ambiguous if someone passed `graph` as a keyword argument.
2. We must ensure explicit parameter support: `analyze_impact(graph=..., findings=..., analysis_id=...)`.
3. If `graph` is provided, Madge runner functions must **never** be invoked under any circumstances.
4. If `repo_path` is provided as fallback, it should only execute Madge when `graph` is explicitly omitted or None.

#### Remediation Plan:
- Refactor `analyze_impact` signature to:
  ```python
  def analyze_impact(
      graph: dict[str, Any] | BaseModel | None = None,
      findings: list[dict[str, Any]] | None = None,
      analysis_id: str = "",
      *,
      repo_path: str | None = None,
  ) -> dict[str, Any]:
  ```
- Support positional first argument for backwards compatibility if passed as `analyze_impact(graph, findings, analysis_id)`.
- Enforce that if `graph` is present, `repo_path` is ignored and Madge is never executed.
- Add spy/mock unit tests verifying zero Madge invocations when `graph` is provided.

---

### 2.4 Task D: Original Finding Data Preservation

#### Existing Code Behavior:
`finding_mapper.py` and `impact_analyzer.py`:
- `extract_finding_adapter` copies top-level keys via `dict(finding)`.
- `enrich_finding` copies keys via `result = dict(adapted_finding)`.
- `EnrichedFinding` has `model_config = ConfigDict(extra="allow")`.

#### Audit Verification:
1. Input mutation check: Original finding dictionaries are not mutated in-place.
2. Field retention check: `finding_id`, `category`, `title`, `file_path`, `start_line`, `end_line`, `symbol`, `source_tool`, `description`, `evidence_class`, `review_risk`, `evidence`, `risk_factors`, `metadata` are preserved.
3. Extra fields: Because `extra="allow"` is configured on `EnrichedFinding`, custom or unexpected fields from upstream tools are preserved upon Pydantic model validation and serialization.
4. Deepcopy safety: We will ensure nested lists and dictionaries (e.g. nested `metadata` or `evidence` items) are deeply preserved and not accidentally overwritten by impact data.

---

## 3. Summary of Required Hardening Actions

1. **Impact Status for Truncated & Partial Graphs**:
   Set `impact_status = IMPACT_STATUS_PARTIAL` when `graph_is_truncated` is True or upstream graph status is `"partial"`.
2. **Explicit Empty vs Unavailable Graph Detection**:
   Distinguish between a valid empty graph (`nodes: [], edges: []`, status `success`) and an unavailable graph (`None`, empty dict, status `unavailable`, status `failed`).
3. **Signature & Duplicate Prevention**:
   Clarify `graph` keyword parameter, ensure Madge is never called when `graph` is provided, and verify orchestrator sequence.
4. **Data Preservation Integration Tests**:
   Create end-to-end integration tests verifying zero data loss across nested finding structures and JSON serialization cycles.

