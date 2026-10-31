# SAMAR_3 --- Dependency & Impact Engine Implementation Plan

**Timebox:** 4 hours (240 minutes) \| **Environment:** Antigravity +
Gemini 3.8 Flash, Medium effort\
**Stack:** Python, Madge, graph algorithms, shared JSON/Pydantic
schemas\
**Deliverable:** Dependency graph, circular dependency detection, test
candidates, and transparent review-priority assessment.

## 1. Mission and Scope

Consume the repository workspace and normalised findings from OM_2.
Produce dependency graph data, cycles, direct impact context,
potentially related tests, and explainable review risk.

### Four-hour success definition

-   Madge runs on the agreed JS/TS fixture.
-   Directed nodes and edges are returned.
-   Circular dependencies are detected.
-   Findings are enriched with direct dependants and context.
-   Potential test files are suggested with reasons and mapping
    strength.
-   Risk labels have explicit contributing factors.
-   TANUJA_4 can call the module as a service.

Do not attempt a sophisticated ML model in this timebox. Use
deterministic rules. Risk means review priority, not probability that
deletion is safe.

## 2. Integration Contract

Agree exact function signatures and file paths with OM_2 and TANUJA_4.

``` python
def analyze_impact(repo_path: str, findings: list[dict], analysis_id: str) -> dict:
    # Return graph, cycles and enriched finding impact context.
    ...
```

### Graph response

``` json
{
  "nodes": [
    {"id": "src/main.ts", "label": "main.ts", "file_path": "src/main.ts", "finding_count": 1, "cycle_member": false}
  ],
  "edges": [
    {"id": "src/main.ts->src/app.ts", "source": "src/main.ts", "target": "src/app.ts", "relationship": "imports"}
  ],
  "cycles": [["src/a.ts", "src/b.ts"]],
  "stats": {"node_count": 2, "edge_count": 1, "cycle_count": 1},
  "truncated": false
}
```

**Edge direction is fixed:** source imports target. BHOOMI_1's React
Flow implementation relies on this.

### Enriched finding

``` json
{
  "finding_id": "f_001",
  "impact": {
    "direct_dependants": ["src/app.ts"],
    "dependency_count": 1,
    "cycle_member": false,
    "related_test_candidates": [
      {
        "file_path": "tests/app.test.ts",
        "reason": "Direct import of the source module",
        "mapping_strength": "direct"
      }
    ],
    "risk_factors": ["The file is imported by another module."],
    "review_risk": "medium"
  }
}
```

## 3. Madge Integration

1.  Pin Madge in the CodeImpact tool environment.
2.  Run against the retrieved JS/TS workspace.
3.  Request machine-readable dependency map.
4.  Retrieve circular dependency output.
5.  Configure extensions and tsconfig handling only when safely
    available.
6.  Normalise paths to repository-relative POSIX paths.
7.  Preserve warnings and tool status.
8.  Do not install target repository dependencies or execute its code.

Dynamic imports and runtime-generated relationships may not be
represented. A missing edge means "not observed by this configured
scan".

## 4. Graph Construction

### Nodes

-   One node per file in dependency map.
-   Stable ID = repository-relative file path.
-   Label = basename.
-   Include finding count and cycle membership.
-   Optionally include in-degree/out-degree.

### Edges

-   Directed source-to-target import relationship.
-   Stable ID derived from source and target.
-   Relationship value `imports`.
-   Deduplicate identical edges.

### Cycles

-   Preserve cycle paths from Madge.
-   Mark every member node.
-   Provide a textual cycle list even if graph UI fails.
-   Do not claim a cycle necessarily causes runtime failure.

### Limits

-   Return bounded nodes/edges.
-   If truncated, include `truncated: true` and original/returned
    counts.
-   Never silently drop graph data.

## 5. Impact Analysis

For each finding with a file path: - Identify direct importers
(dependants) using the agreed edge direction. - Identify direct imports
made by that file. - Check cycle membership. - Calculate simple degree
counts. - Check entry-point indicators where possible.

Possible entry-point indicators: `src/main.*`, `src/index.*`, root
`index.*`, or configured package entry points. Treat conventions as
signals, not universal truth. Evidence status should be
found/not_found/unknown/not_checked.

Avoid all-pairs graph calculations; one-hop context is sufficient for
the MVP.

## 6. Test Impact Mapping

### Four-hour heuristics

1.  Inventory common test paths and patterns:
    -   `*.test.js`, `*.test.ts`, `*.spec.js`, `*.spec.ts`
    -   `__tests__/**`
    -   `tests/**`
2.  Compare source/test basenames and relative directories.
3.  Inspect test imports when practical.
4.  Prefer direct source import matches.
5.  Use name/path similarity as weaker evidence.
6.  Return reason and mapping strength for every candidate.

Mapping strength: - `direct`: test imports the source file. -
`heuristic`: basename/path similarity. - `unknown`: test
inventory/import parsing unavailable.

Use wording "potentially related test candidates", never "all affected
tests" or "complete coverage".

## 7. Review-Risk Rules

Inputs: - Direct dependant count - Entry-point indicator - Cycle
membership - Dynamic/framework usage indicators if available - Test
candidate evidence - Evidence completeness - Finding category

Suggested transparent rules: - **Higher:** entry-point indicator found,
multiple direct dependants, or cycle membership. - **Medium:** one
direct dependant, uncertain framework/dynamic usage, or incomplete test
mapping. - **Lower:** no observed direct dependants, no
entry-point/cycle signal, and adequate configured coverage. -
**Unknown:** graph failed, file absent from inventory, or critical
evidence unavailable.

Return exact factors, e.g.: - `entry_point_indicator_found` -
`direct_dependants:2` - `cycle_member` - `dynamic_usage_unknown` -
`test_mapping_heuristic` - `graph_coverage_partial`

Do not automatically assign Lower when evidence is missing. Do not
output a deletion-safety percentage.

## 8. Four-Hour Execution Plan

  -----------------------------------------------------------------------
  Time                    Work                    Output
  ----------------------- ----------------------- -----------------------
  00--20 min              Agree schemas and       Interface locked
                          function signatures     

  20--55                  Integrate Madge and     Dependency map
                          inspect fixture output  

  55--90                  Normalise nodes, edges, Graph JSON
                          cycles                  

  90--120                 Direct dependants and   Impact context
                          one-hop impact          

  120--155                Test inventory and      Test candidates
                          mapping heuristics      

  155--185                Review-risk rules and   Risk output
                          factor breakdown        

  185--210                Integrate enriched      Callable service
                          findings and graph      

  210--230                Test cycles, missing    Robust output
                          tool, paths and graph   
                          limits                  

  230--240                Handoff and commit      Verified module
  -----------------------------------------------------------------------

## 9. Suggested Structure

``` text
backend/app/
  services/
    impact_service.py
    dependency_graph_service.py
    test_impact_service.py
    review_risk_engine.py
  analyzers/
    madge_runner.py
  schemas/
    graph.py
    impact.py
    risk.py
backend/tests/
  fixtures/dependency_fixture/
  test_madge_parser.py
  test_graph_builder.py
  test_test_impact.py
  test_risk_engine.py
```

## 10. Antigravity Prompts

**Prompt A --- Inspect contracts** \> Inspect the existing CodeImpact
repository and shared schemas. Implement the dependency/impact module as
an importable service, not a second API app. Use the exact repository
workspace and finding contracts. Confirm edge direction is source
imports target. Do not rename shared fields.

**Prompt B --- Madge and graph** \> Integrate a pinned Madge version for
JS/TS dependency analysis. Parse its JSON dependency map and cycle
output. Normalise paths to repository-relative POSIX paths. Return
stable nodes, directed edges, cycle paths, graph stats and truncation
flag. Do not install target dependencies or execute code. Add fixture
tests.

**Prompt C --- Impact and tests** \> Implement direct dependant
calculation and a lightweight test impact mapper. Detect common test
patterns and map candidates through direct imports first, then
basename/path similarity. Return mapping strength and reason. Do not
claim complete test coverage.

**Prompt D --- Risk** \> Implement deterministic, explainable
review-risk rules using only available graph/evidence signals. Return
lower/medium/higher/unknown and exact risk factors. Missing evidence
must remain unknown. Do not output safe-to-delete probability or
automatic deletion advice.

**Prompt E --- Audit** \> Test edge direction, cycle membership, path
normalisation, dependants, test mapping, risk factors, partial Madge
failure and graph truncation. Ensure output matches the shared API
contract exactly.

## 11. Testing Checklist

-   [ ] Madge runs on JS/TS fixture.
-   [ ] Dependency output parses.
-   [ ] Edge direction is source-imports-target.
-   [ ] Node IDs are stable repository-relative paths.
-   [ ] Duplicate edges are removed.
-   [ ] Cycles and cycle members are correct.
-   [ ] Direct dependants are correct.
-   [ ] Test candidates include reason and strength.
-   [ ] Risk factors explain the risk label.
-   [ ] Unknown evidence does not become Lower automatically.
-   [ ] Tool failure is not represented as successful empty graph.
-   [ ] Graph truncation is explicit.
-   [ ] TANUJA_4 can import the service.

## 12. Handoff

Provide function signature, graph/enriched finding samples, Madge
version/command, edge-direction statement, risk rules, test-mapping
limitations and actual test results.

**Final deliverable:** tested dependency/impact service with graph,
cycle detection, test candidates and explainable review priority.
