# SAMAR_3 — Dependency & Impact Engine
## Phase-Wise Detailed Implementation Plan

**Owner:** SAMAR_3 — Dependency & Impact Engine  
**Total timebox:** 4 hours (240 minutes)  
**Environment:** Antigravity IDE + Gemini 3.8 Flash (Medium effort)  
**Stack:** Python, Madge, graph algorithms, shared JSON/Pydantic schemas  
**Primary deliverable:** An importable dependency and impact service that returns a repository dependency graph, circular dependencies, finding impact context, potentially related test candidates, and transparent review-priority labels.

---

# 1. Mission and Scope

Build the dependency and impact layer for CodeImpact. The service consumes:

- A local, already-retrieved repository workspace.
- Normalised findings produced by **OM_2 — Static Code Analysis**.
- A unique `analysis_id`.

It produces:

- A directed dependency graph.
- Circular dependency paths and cycle membership.
- Direct dependencies and direct dependants for each relevant finding.
- Potentially related test-file candidates with evidence and mapping strength.
- Explainable review-risk labels and contributing factors.

## Explicit MVP boundaries

- Focus on JavaScript/TypeScript repositories supported by the agreed Madge configuration.
- Use deterministic rules; do not build or train an ML model in this four-hour task.
- Do not install dependencies from the target repository or execute its scripts/code.
- Do not automatically delete files, modify source code, apply patches, or create commits.
- Do not interpret an absent dependency edge as proof that a file is unused. Dynamic imports, aliases, framework conventions, generated code and runtime loading can be missed.
- A review-risk label is a prioritisation signal, **not** a probability that deletion is safe.

## Definition of done

1. Madge can analyse the agreed JS/TS fixture without running target code.
2. The service returns stable, repository-relative nodes and correctly directed edges.
3. Circular dependency paths and member flags are represented.
4. Each file-based finding can be enriched with one-hop impact context.
5. Potential test candidates include a reason and mapping strength.
6. Risk labels include explicit evidence factors; missing critical evidence remains `unknown`.
7. TANUJA_4 can import and call the service using the agreed function signature.
8. Tests cover normal output, cycles, missing files/tool failures, path handling and truncation.

---

# 2. Integration Contract — Lock Before Coding

**Time allocation:** 0–20 minutes  
**Depends on:** OM_2's finding schema and the shared backend structure.  
**Handoff partners:** OM_2 and TANUJA_4; BHOOMI_1 consumes the graph response.

## 2.1 Required function signature

Keep the shared service callable without creating a separate FastAPI application:

```python
def analyze_impact(
    repo_path: str,
    findings: list[dict],
    analysis_id: str,
) -> dict:
    """Return dependency graph and finding-level impact context."""
```

If the repository already defines Pydantic models, use them rather than introducing competing schemas. Do not rename agreed shared fields without approval from the team.

## 2.2 Graph response contract

```json
{
  "analysis_id": "analysis_123",
  "graph": {
    "nodes": [
      {
        "id": "src/main.ts",
        "label": "main.ts",
        "file_path": "src/main.ts",
        "finding_count": 1,
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
    "cycles": [],
    "stats": {
      "node_count": 2,
      "edge_count": 1,
      "cycle_count": 0,
      "original_node_count": 2,
      "original_edge_count": 1,
      "returned_node_count": 2,
      "returned_edge_count": 1
    },
    "truncated": false
  },
  "enriched_findings": []
}
```

**Mandatory edge direction:** `source` imports `target`. For example, `src/main.ts -> src/app.ts` means `main.ts` imports `app.ts`. BHOOMI_1's React Flow view depends on this convention.

## 2.3 Enriched finding contract

```json
{
  "finding_id": "f_001",
  "impact": {
    "direct_dependants": ["src/app.ts"],
    "direct_dependencies": ["src/utils.ts"],
    "dependency_count": 1,
    "dependant_count": 1,
    "cycle_member": false,
    "entry_point_evidence": "not_found",
    "related_test_candidates": [
      {
        "file_path": "tests/app.test.ts",
        "reason": "Test file directly imports the source module",
        "mapping_strength": "direct"
      }
    ],
    "risk_factors": ["direct_dependants:1"],
    "review_risk": "medium"
  }
}
```

## 2.4 Contract rules

- Paths must be repository-relative POSIX paths, for example `src/app.ts`.
- Node IDs must be stable and equal to the normalised file path.
- `review_risk` must be one of `lower`, `medium`, `higher`, or `unknown`.
- `mapping_strength` must be one of `direct`, `heuristic`, or `unknown`.
- Evidence status must distinguish `found`, `not_found`, `unknown`, and `not_checked` where applicable.
- Graph truncation must be explicit and include original and returned counts.

### Phase 1 completion gate

Do not begin implementation until the function signature, edge direction, finding identifiers, file-path field and graph response shape have been confirmed with the other owners.

### Antigravity Prompt — Phase 1

> Inspect the existing CodeImpact repository and identify the shared finding schema, backend package structure, repository workspace convention and existing tests. Prepare the dependency-impact service integration contract using `analyze_impact(repo_path: str, findings: list[dict], analysis_id: str) -> dict`. Confirm with the existing code that graph edges mean source imports target. Reuse existing Pydantic models and field names wherever possible. Do not create a second API application, do not rename shared fields, and do not modify unrelated modules. Report the exact files and contract decisions before coding.

---

# 3. Phase 2 — Madge Setup and Dependency Extraction

**Time allocation:** 20–55 minutes (35 minutes)  
**Depends on:** Phase 1 contract locked.  
**Goal:** Obtain a machine-readable dependency map and circular dependency output from the checked-out repository workspace.

## 3.1 Implementation tasks

1. Check whether Madge is already available in the project/tool environment.
2. Pin or document a known Madge version in the CodeImpact analysis environment; do not install packages from the target repository.
3. Invoke Madge against the supplied repository workspace using a bounded subprocess call.
4. Request machine-readable JSON dependency-map output.
5. Request circular dependency output separately if required by the selected Madge invocation.
6. Configure JS/TS extensions and TypeScript configuration only when the relevant configuration is safely available.
7. Capture standard output, standard error, exit status and timeout state.
8. Parse the result and preserve tool warnings.
9. Normalise all returned paths to repository-relative POSIX paths.

## 3.2 Execution safety requirements

- Use an argument list, not a shell command string (`shell=False`).
- Set a subprocess timeout.
- Set a working directory to the supplied workspace.
- Do not execute `npm install`, `yarn`, `pnpm install`, package scripts or repository code.
- Bound captured output and report parser/tool errors without dumping secrets or full file contents.
- Treat missing Madge, timeout, invalid JSON and non-zero exit status as explicit analysis states.

## 3.3 Suggested internal result

```python
{
    "status": "success",  # success | partial | failed
    "dependency_map": {
        "src/main.ts": ["src/app.ts"],
        "src/app.ts": ["src/utils.ts"]
    },
    "cycles": [],
    "warnings": [],
    "error": None
}
```

Do not turn a failed Madge run into a successful empty dependency map. A successful scan that observes zero imports is different from a scan that did not run.

## 3.4 Expected files

- `backend/app/analyzers/madge_runner.py`
- `backend/tests/test_madge_parser.py`
- A small fixture repository under `backend/tests/fixtures/dependency_fixture/`

### Phase 2 testing

- Run Madge against a fixture containing at least three JS/TS files with known imports.
- Confirm the JSON output parses.
- Confirm a missing executable and malformed output are handled as failures.
- Confirm a timeout is surfaced rather than hidden.
- Confirm paths outside the repository root are rejected or safely marked invalid.

### Phase 2 completion gate

A callable Madge runner returns a structured success/partial/failed result and does not execute target repository code.

### Antigravity Prompt — Phase 2

> Implement `madge_runner.py` for CodeImpact. Integrate a pinned Madge version in the analysis environment and invoke it only against the supplied JS/TS workspace. Use subprocess with an argument list, `shell=False`, a timeout, bounded output and explicit exit-status handling. Parse the machine-readable dependency map and circular dependency output. Normalise paths to repository-relative POSIX paths. Do not install target-repository dependencies or execute its scripts. Return structured `success`, `partial` or `failed` status, warnings and error information. Add fixture tests for valid output, malformed output, missing Madge and timeout. Do not proceed to graph construction until the runner tests pass.

---

# 4. Phase 3 — Dependency Graph Construction

**Time allocation:** 55–90 minutes (35 minutes)  
**Depends on:** Phase 2 returns a parsed dependency map.  
**Goal:** Convert Madge output into the stable graph contract used by the frontend and impact engine.

## 4.1 Node construction

For every file represented in the dependency map:

- `id`: stable repository-relative file path.
- `label`: file basename.
- `file_path`: same normalised path.
- `finding_count`: number of normalised findings referring to the file.
- `cycle_member`: whether the file belongs to at least one detected cycle.
- `in_degree`: number of files importing this file.
- `out_degree`: number of imports made by this file.

A file with a finding but absent from the dependency map should not be silently invented as a fully analysed node. Preserve its impact state as missing/unknown, or add a clearly marked isolated node only if the shared graph contract explicitly permits it.

## 4.2 Edge construction

For each `source -> target` relationship in Madge's dependency map:

- `source` is the importing file.
- `target` is the imported file.
- `relationship` is `imports`.
- `id` is deterministic, for example `src/main.ts->src/app.ts`.
- Deduplicate repeated source-target pairs.

## 4.3 Cycle construction

- Preserve each cycle path returned by Madge.
- Mark every file in a returned cycle as `cycle_member: true`.
- Keep a textual cycle list even if the graph UI cannot render it.
- Do not imply that every cycle causes a runtime failure.
- Avoid inventing cycles from incomplete or failed graph data.

## 4.4 Graph bounds and truncation

Use conservative maximum node/edge limits suitable for the current UI. Keep limits configurable. If the graph is truncated:

- Set `truncated: true`.
- Preserve original and returned node/edge counts.
- Apply deterministic ordering before truncating.
- Never silently discard graph data or report returned counts as original counts.

## 4.5 Expected files

- `backend/app/services/dependency_graph_service.py`
- `backend/app/schemas/graph.py` (only if a shared graph schema does not already exist)
- `backend/tests/test_graph_builder.py`

### Phase 3 testing

- Verify source-imports-target edge direction.
- Verify stable IDs and POSIX paths.
- Verify duplicate edges are removed.
- Verify degree counts.
- Verify cycle paths and all cycle-member flags.
- Verify truncation metadata and deterministic output order.

### Phase 3 completion gate

A graph fixture produces exactly the expected nodes, edges, cycle membership, statistics and truncation state.

### Antigravity Prompt — Phase 3

> Implement the dependency graph builder using the parsed Madge result and the locked graph contract. Build stable repository-relative node IDs, directed source-imports-target edges, deterministic edge IDs, deduplicated relationships, degree counts, finding counts and cycle-member flags. Preserve cycle paths. Add configurable graph limits; when truncating, include original and returned counts and set `truncated: true`. Do not silently omit graph data. Add tests for edge direction, path normalisation, duplicates, degrees, cycles and truncation. Reuse existing schemas and do not change the frontend contract.

---

# 5. Phase 4 — Finding-Level Impact Analysis

**Time allocation:** 90–120 minutes (30 minutes)  
**Depends on:** Phase 3 graph builder.  
**Goal:** Enrich each OM_2 finding with simple, evidence-backed one-hop dependency context.

## 5.1 Impact calculation

For each finding containing a valid file path:

1. Normalise and validate the path relative to the repository root.
2. Identify **direct dependants**: files whose imports point to the finding's file.
3. Identify **direct dependencies**: files imported by the finding's file.
4. Calculate direct dependant and dependency counts.
5. Check whether the file is a member of a known cycle.
6. Check for entry-point indicators using repository conventions.
7. Record missing or incomplete evidence explicitly.

Do not implement expensive all-pairs graph calculations. One-hop context is enough for this MVP.

## 5.2 Entry-point indicators

Possible indicators include:

- `src/main.*`
- `src/index.*`
- Root-level `index.*`
- Configured package entry points, when safely available.

These are conventions, not universal truths. Return an evidence status such as `found`, `not_found`, `unknown` or `not_checked`; do not claim a file is definitely an application entry point based only on its name.

## 5.3 Missing-file handling

If a finding points to a path that is absent from the graph or repository inventory:

- Do not treat it as having zero dependants.
- Set the relevant impact evidence to `unknown`.
- Preserve the original finding.
- Add a concise reason to the impact result.

## 5.4 Expected files

- `backend/app/services/impact_service.py`
- `backend/tests/test_impact_service.py`

### Phase 4 testing

Use a fixture where `main.ts` imports `app.ts`, and `app.ts` imports `utils.ts`. Confirm the direct dependants and dependencies for each file. Also test a finding that refers to a missing file and a file in a cycle.

### Phase 4 completion gate

Every supported file-based finding receives correct one-hop context, while missing evidence remains explicitly unknown.

### Antigravity Prompt — Phase 4

> Implement finding-level one-hop impact analysis over the graph. For each finding with a file path, calculate direct importers as direct dependants and outgoing imports as direct dependencies, respecting the fixed source-imports-target convention. Add direct counts, cycle membership and cautious entry-point indicators. Validate paths against the repository root. If the file or graph evidence is unavailable, mark the result unknown rather than assigning zero impact. Avoid all-pairs graph algorithms. Add tests for known relationships, cycles, entry-point indicators and missing files.

---

# 6. Phase 5 — Potential Test Impact Mapping

**Time allocation:** 120–155 minutes (35 minutes)  
**Depends on:** Phase 4 file-level impact context.  
**Goal:** Suggest potentially related test files and explain why each candidate is relevant.

## 6.1 Test-file inventory

Recognise common patterns, including:

- `*.test.js`, `*.test.ts`
- `*.spec.js`, `*.spec.ts`
- `__tests__/**`
- `tests/**`

Extend patterns only when the repository makes the convention clear. Do not assume every project follows the same test layout.

## 6.2 Candidate matching order

1. **Direct evidence:** inspect test imports where practical and identify tests that directly import the source module.
2. **Heuristic evidence:** compare source/test basenames and relative directory structure.
3. **Unknown:** if the test inventory or import parsing is unavailable, report that limitation.

Each candidate must include:

- `file_path`
- `reason`
- `mapping_strength`: `direct`, `heuristic` or `unknown`

Example:

```json
{
  "file_path": "tests/app.test.ts",
  "reason": "Test file directly imports src/app.ts",
  "mapping_strength": "direct"
}
```

## 6.3 Required wording and limitations

Use **“potentially related test candidates”**. Do not say “all affected tests”, “complete test coverage” or imply that a candidate test guarantees coverage of the finding. A heuristic name match is weaker evidence than a parsed direct import.

## 6.4 Expected files

- `backend/app/services/test_impact_service.py`
- `backend/tests/test_test_impact.py`

### Phase 5 testing

- A direct import produces `mapping_strength: direct`.
- A basename/path-only match produces `heuristic`.
- Unavailable inventory/import parsing produces `unknown` or an explicit unavailable state.
- Every candidate has a reason.
- Candidate ordering is deterministic.

### Phase 5 completion gate

The service returns explainable candidate tests without claiming complete coverage.

### Antigravity Prompt — Phase 5

> Implement a lightweight test impact mapper. Inventory common JS/TS test patterns (`*.test.*`, `*.spec.*`, `__tests__`, and `tests`). Prefer direct test imports of the source module; use basename and relative-path similarity only as weaker heuristic evidence. Return each candidate's repository-relative path, reason and mapping strength (`direct`, `heuristic` or `unknown`). If test inventory or import parsing is unavailable, preserve that uncertainty. Use the phrase “potentially related test candidates” in user-facing descriptions; never claim complete test coverage. Add deterministic fixture tests.

---

# 7. Phase 6 — Explainable Review-Risk Engine

**Time allocation:** 155–185 minutes (30 minutes)  
**Depends on:** Phases 3–5 evidence.  
**Goal:** Assign a transparent review-priority label based on observable evidence and uncertainty.

## 7.1 Inputs

Use only available signals, such as:

- Direct dependant count.
- Entry-point indicator status.
- Cycle membership.
- Dynamic/framework usage uncertainty, if detected by an existing safe scan.
- Test candidate mapping strength and inventory completeness.
- Graph scan status and evidence completeness.
- Finding category from OM_2.

Do not invent signals that are not available in the current repository scan.

## 7.2 Deterministic MVP rules

| Review risk | Suggested conditions |
|---|---|
| `higher` | Entry-point indicator found, multiple direct dependants, or cycle membership. |
| `medium` | One direct dependant, uncertain framework/dynamic usage, or incomplete test mapping. |
| `lower` | No observed direct dependants, no entry-point/cycle signal, and adequate configured evidence coverage. |
| `unknown` | Graph failed, file is absent from inventory, or critical evidence is unavailable. |

**Precedence:** critical missing evidence must not be converted into `lower`. If the graph failed or the file cannot be validated, return `unknown`. If multiple signals apply, preserve all factors and choose the more cautious applicable label.

## 7.3 Risk factors

Return exact machine-readable factors, for example:

- `entry_point_indicator_found`
- `direct_dependants:2`
- `cycle_member`
- `dynamic_usage_unknown`
- `test_mapping_heuristic`
- `graph_coverage_partial`

Also provide concise human-readable explanations if the existing API contract supports them.

## 7.4 Safety language

- Use “review priority” or “review risk”.
- Never output a deletion-safety percentage.
- Never recommend automatic deletion.
- `lower` means lower observed review priority under the configured scan, not safe to delete.

## 7.5 Expected files

- `backend/app/services/review_risk_engine.py`
- `backend/tests/test_risk_engine.py`

### Phase 6 testing

Test every risk level, combinations of factors, failed graph status, missing file evidence and partial test mapping. Specifically verify that missing evidence cannot become `lower`.

### Phase 6 completion gate

Every risk label is reproducible from its returned factors, and uncertainty is handled conservatively.

### Antigravity Prompt — Phase 6

> Implement a deterministic, explainable review-risk engine using only the impact, graph and test evidence already available. Return `lower`, `medium`, `higher` or `unknown`, plus exact contributing risk factors. Apply conservative precedence: failed graph analysis, missing file inventory or unavailable critical evidence must not become `lower`. Use entry-point indicators, direct dependant counts, cycle membership, test mapping strength and evidence completeness. Do not train a model, generate a deletion-safety percentage, or claim that any file is safe to delete. Add unit tests for every label and important combinations.

---

# 8. Phase 7 — Service Orchestration and Team Integration

**Time allocation:** 185–210 minutes (25 minutes)  
**Depends on:** Phases 2–6.  
**Goal:** Connect the modules behind the single agreed `analyze_impact` entry point.

## 8.1 Orchestration sequence

The service should perform the following steps in order:

1. Validate `repo_path` and `analysis_id`.
2. Accept OM_2's normalised findings without changing their shared fields.
3. Run Madge and capture its structured status.
4. Build graph data when dependency extraction succeeds.
5. Enrich file-based findings with one-hop impact context.
6. Identify potentially related test candidates.
7. Calculate review-risk labels and factors.
8. Return the graph, enriched findings, status, warnings and analysis identifier in the agreed response shape.

If Madge fails, return a structured partial/failed result and mark graph-dependent impact evidence as unknown. Do not fabricate an empty successful graph.

## 8.2 Suggested module structure

```text
backend/app/
  analyzers/
    madge_runner.py
  services/
    impact_service.py
    dependency_graph_service.py
    test_impact_service.py
    review_risk_engine.py
  schemas/
    graph.py
    impact.py
    risk.py
backend/tests/
  fixtures/
    dependency_fixture/
  test_madge_parser.py
  test_graph_builder.py
  test_impact_service.py
  test_test_impact.py
  test_risk_engine.py
```

Reuse the existing project layout if it differs. Do not create duplicate schema or service directories just to match this example.

## 8.3 Integration with teammates

- **OM_2:** confirm finding IDs, category and file-path field; do not mutate their original findings.
- **TANUJA_4:** expose/import `analyze_impact`; agree how the service's status and errors are returned by the API.
- **BHOOMI_1:** provide the exact graph sample, edge direction and truncation behaviour for React Flow.

### Phase 7 testing

- Import and call `analyze_impact` from a test or small integration script.
- Verify the result contains `analysis_id`, graph and enriched findings.
- Verify OM_2 fields remain unchanged outside the added impact object.
- Verify Madge failure propagates as explicit uncertainty.

### Phase 7 completion gate

TANUJA_4 can call the service through the agreed function signature and BHOOMI_1 can consume the graph response without adapting field meanings.

### Antigravity Prompt — Phase 7

> Integrate the completed Madge runner, graph builder, impact analyser, test mapper and review-risk engine behind `analyze_impact(repo_path, findings, analysis_id)`. Preserve OM_2's original finding fields and attach impact data using the agreed contract. Return graph status, warnings and analysis ID. On Madge failure, report structured failure/partial status and unknown graph-dependent evidence; never fake a successful empty graph. Add an integration test that TANUJA_4 can use to import and call the service. Do not create a separate FastAPI app or alter BHOOMI_1's graph contract.

---

# 9. Phase 8 — Regression, Hardening and Handoff

**Time allocation:** 210–240 minutes (30 minutes)  
**Depends on:** Phase 7 integration.  
**Goal:** Run the focused test suite, fix contract defects and hand off a verified module.

## 9.1 Required validation checklist

### Madge and safety
- [ ] Madge runs against the JS/TS fixture.
- [ ] Target repository dependencies are not installed.
- [ ] Target repository code/scripts are not executed.
- [ ] Subprocess uses `shell=False`, timeout and bounded output.
- [ ] Tool failure is not represented as a successful empty graph.

### Graph
- [ ] Dependency output parses correctly.
- [ ] Edge direction is source imports target.
- [ ] Node IDs are stable repository-relative POSIX paths.
- [ ] Duplicate edges are removed.
- [ ] Degree counts are correct.
- [ ] Cycles and cycle-member flags are correct.
- [ ] Graph truncation is explicit and includes original/returned counts.

### Impact and tests
- [ ] Direct dependants are correct.
- [ ] Direct dependencies are correct.
- [ ] Missing files remain unknown rather than zero-impact.
- [ ] Entry-point indicators are presented as evidence, not certainty.
- [ ] Test candidates include a reason and mapping strength.
- [ ] Heuristic matches are not presented as direct evidence.
- [ ] No claim of complete test coverage is made.

### Review risk and integration
- [ ] Risk factors explain the returned label.
- [ ] Missing critical evidence does not become `lower`.
- [ ] No deletion-safety percentage is returned.
- [ ] OM_2 finding fields remain intact.
- [ ] TANUJA_4 can import and call the service.
- [ ] Graph response matches BHOOMI_1's contract.

## 9.2 Handoff package

Provide the team with:

1. Final function signature and import path.
2. Example graph JSON and enriched finding JSON.
3. Madge version and exact invocation/configuration used.
4. Explicit statement that edge direction is source imports target.
5. Risk rules and risk-factor definitions.
6. Test-mapping heuristics and known limitations.
7. Graph limits and truncation behaviour.
8. Actual test command and pass/fail result.
9. Known limitations or unfinished items; do not report untested functionality as complete.

### Phase 8 completion gate

The focused test suite passes, the service is callable by TANUJA_4, and the handoff documents the actual behaviour and limitations.

### Antigravity Prompt — Phase 8

> Perform final regression and hardening for SAMAR_3's dependency-impact service. Run the focused tests for Madge parsing, graph construction, edge direction, cycles, direct dependants, test candidate mapping, risk rules, missing files, tool failures and graph truncation. Fix only defects within this module and preserve the agreed shared contracts. Verify `analyze_impact(repo_path, findings, analysis_id)` can be imported and called. Produce a concise handoff report containing the exact test command and actual results, Madge version, edge-direction convention, risk rules, mapping limitations, graph limits and any known issues. Do not claim tests passed unless they were actually run.

---

# 10. Four-Hour Phase Schedule

| Phase | Time | Duration | Main output |
|---|---:|---:|---|
| Phase 1 — Contract and repository inspection | 00–20 min | 20 min | Locked interface and schema decisions |
| Phase 2 — Madge setup and extraction | 20–55 min | 35 min | Structured dependency map and cycles |
| Phase 3 — Graph construction | 55–90 min | 35 min | Stable graph JSON |
| Phase 4 — Finding impact analysis | 90–120 min | 30 min | Direct dependencies/dependants and evidence |
| Phase 5 — Test impact mapping | 120–155 min | 35 min | Potentially related test candidates |
| Phase 6 — Review-risk engine | 155–185 min | 30 min | Explainable risk labels and factors |
| Phase 7 — Orchestration and integration | 185–210 min | 25 min | Callable `analyze_impact` service |
| Phase 8 — Regression and handoff | 210–240 min | 30 min | Verified module and handoff notes |
| **Total** | **00–240 min** | **240 min** | **Integrated dependency-impact engine** |

## Timebox rule

If time is running short, prioritise the working end-to-end path: Madge extraction → graph → direct impact → risk → callable service. Keep test mapping lightweight and document any unsupported case. Do not sacrifice safety handling, contract compatibility or truthful failure reporting to add extra features.

---

# 11. Final Deliverable Summary

At the end of the four hours, SAMAR_3 should hand off:

- A Madge runner with safe subprocess handling.
- A stable directed dependency graph with cycle information.
- Finding-level one-hop dependency and dependant context.
- Potentially related test candidates with evidence strength.
- Deterministic, explainable review-risk labels.
- One importable `analyze_impact` service.
- Focused tests and a truthful handoff report.

**Final principle:** CodeImpact provides evidence to help developers review code. It does not decide that code is safe to delete, and it never deletes or changes repository code automatically.
