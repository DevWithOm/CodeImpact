# OM_2 --- Static Code Analysis Implementation Plan

**Timebox:** 4 hours (240 minutes) \| **Environment:** Antigravity +
Gemini 3.8 Flash, Medium effort\
**Stack:** GitHub retrieval, Node.js tooling (Knip, jscpd), Python
service adapter\
**Deliverable:** Real, normalised static-analysis findings from a safely
retrieved public repository.

## 1. Mission and Scope

Implement repository retrieval, JS/TS project detection, Knip
unused-code detection, jscpd duplicate-code detection, and a standard
JSON output that SAMAR_3 and TANUJA_4 can consume.

### Must deliver

-   Public GitHub repository retrieval with optional branch.
-   Safe temporary workspace.
-   Knip integration for unused files/exports/dependencies where
    supported.
-   jscpd integration for duplicate code.
-   Normalised findings with file paths, available line numbers,
    categories and source tool.
-   Tool coverage and partial-failure reporting.
-   Importable service functions; do not create a second FastAPI server.

### Out of scope

All-language support, semantic proof of dead code, running repository
code, installing target dependencies, and automatic cleanup/deletion.

## 2. Integration Contract

Coordinate with TANUJA_4 on exact file paths and function signatures.

``` python
def retrieve_repository(repository_url: str, branch: str | None = None) -> dict:
    # Return workspace_path and repository metadata for internal use.
    ...

def analyze_repository(repo_path: str, analysis_id: str) -> dict:
    # Return normalised findings and tool coverage.
    ...
```

### Finding schema

``` json
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
      "details": "No reference was returned by this configured scan."
    }
  ],
  "risk_factors": [],
  "metadata": {}
}
```

Categories: `unused_file`, `unused_export`, `unused_dependency`,
`duplicate_code`, `other`. Use `null` for unavailable line numbers.
Never fabricate locations.

### Tool coverage

``` json
{
  "knip": {"status": "completed", "finding_count": 7, "message": null},
  "jscpd": {"status": "partial", "finding_count": 2, "message": "Some files were skipped."}
}
```

Statuses: `completed`, `partial`, `failed`, `skipped`. A failed tool is
not equivalent to zero findings.

## 3. Repository Retrieval

### Accepted input

-   HTTPS GitHub repository URL.
-   Optional branch; resolve default branch if omitted.

### Safety requirements

-   Allow only `github.com`; reject unsupported schemes/hosts and
    embedded credentials.
-   Use shallow clone or GitHub API download with strict time,
    file-count and byte limits.
-   Use a unique temporary workspace per analysis.
-   Do not execute repository code.
-   Do not run `npm install`, `npm ci`, build scripts, tests, or package
    lifecycle scripts.
-   Avoid symlink/path traversal outside the workspace.
-   Ignore `.git`, `node_modules`, build outputs, coverage,
    generated/minified files as appropriate.
-   Clean temporary workspaces according to retention policy.
-   Never log tokens, credentials or secrets.

### Retrieval result

``` json
{
  "workspace_path": "/tmp/codeimpact/an_123",
  "repository": "owner/repository",
  "branch": "main",
  "commit_sha": "abc123",
  "file_count": 120,
  "languages": ["TypeScript", "JavaScript"],
  "status": "retrieved"
}
```

The workspace path is internal and must never be sent to the browser.

## 4. Knip Integration

1.  Detect `package.json` and JS/TS source.
2.  Pin a Knip version in CodeImpact's tool environment.
3.  Use the JSON output mode supported by that exact version.
4.  Parse unused file, export and dependency results.
5.  Preserve path, symbol and line number only if reported.
6.  Respect project configuration and entry points when available.
7.  Capture warnings and mark coverage partial when
    configuration/dependency resolution limits analysis.
8.  Do not install target repository dependencies or run its scripts.

Dynamic imports, reflection, framework registration and generated usage
may cause false positives. Phrase results as "potentially unused" or "no
static reference found".

## 5. jscpd Integration

1.  Pin a jscpd version.
2.  Run against supported JS/TS files with configured exclusions and
    thresholds.
3.  Request JSON output.
4.  Parse duplicate blocks and all reported locations.
5.  Normalise one finding per duplicate group, keeping other locations
    in `metadata.duplicates`.
6.  Preserve reported line ranges and similarity only when actually
    supplied.
7.  Do not invent similarity percentages.

Example:

``` json
{
  "finding_id": "f_dup_01",
  "category": "duplicate_code",
  "title": "Duplicate code block",
  "file_path": "src/a.ts",
  "start_line": 20,
  "end_line": 35,
  "source_tool": "jscpd",
  "evidence_class": "strong",
  "review_risk": "unknown",
  "evidence": [
    {"kind": "duplicate_block", "status": "found", "source": "jscpd", "details": "Matching block reported in src/b.ts."}
  ],
  "metadata": {
    "duplicates": [{"file_path": "src/b.ts", "start_line": 8, "end_line": 23}]
  }
}
```

## 6. Safe Tool Runner

Use a reusable subprocess wrapper: - Argument arrays, never shell
command concatenation. - `shell=False`. - Explicit working directory. -
Strict timeout. - Bounded stdout/stderr capture. - Exit code and
elapsed-time capture. - Structured timeout/non-zero/malformed-output
errors. - Do not expose raw stderr or stack traces to the frontend.

## 7. Four-Hour Execution Plan

  -----------------------------------------------------------------------
  Time                    Work                    Output
  ----------------------- ----------------------- -----------------------
  00--20 min              Agree service contract  Callable interface
                          and create analyzer     
                          module                  

  20--55                  Implement safe GitHub   Workspace + metadata
                          retrieval and metadata  
                          detection               

  55--85                  Build safe subprocess   Reusable execution
                          runner                  utility

  85--130                 Integrate Knip and JSON Unused-code findings
                          parser                  

  130--165                Integrate jscpd and     Duplicate findings
                          JSON parser             

  165--190                Normalise IDs, paths,   Standard JSON
                          categories and evidence 

  190--215                Add coverage/error      Partial-safe output
                          handling and fixtures   

  215--230                Integrate with          Importable services
                          SAMAR_3/TANUJA_4        

  230--240                Run fixture test,       Verified module
                          commit, handoff         
  -----------------------------------------------------------------------

## 8. Suggested Structure

``` text
backend/app/
  services/
    repository_retrieval.py
    static_analysis_service.py
  analyzers/
    safe_subprocess.py
    knip_runner.py
    jscpd_runner.py
    output_normalizer.py
  schemas/
    finding.py
    analysis_coverage.py
backend/tests/
  fixtures/sample_js_repo/
  test_repository_retrieval.py
  test_knip_parser.py
  test_jscpd_parser.py
  test_normalizer.py
```

If tools run in a separate Node workspace, document exact pinned
versions, commands and output formats. Avoid maintaining duplicate
parser logic.

## 9. Antigravity Prompts

**Prompt A --- Retrieval** \> Inspect the existing CodeImpact repository
and implement safe public GitHub retrieval as an importable service, not
a new FastAPI app. Validate HTTPS github.com URLs, resolve
branch/default branch, capture commit metadata, use an isolated
temporary workspace, enforce size/file/time limits, and never execute
repository code or package scripts. Add tests.

**Prompt B --- Subprocess** \> Implement a reusable analyzer subprocess
runner using argument arrays, shell=False, explicit cwd, timeouts and
bounded output. Return structured errors for timeout, non-zero exit and
malformed JSON. Add tests.

**Prompt C --- Knip** \> Integrate a pinned Knip version for JS/TS. Use
that version's supported JSON output. Parse unused files, exports and
dependencies into the shared Finding schema. Preserve only actual tool
locations; do not install target dependencies or run lifecycle scripts.
Add fixture parser tests.

**Prompt D --- jscpd** \> Integrate pinned jscpd and parse its JSON
report into duplicate_code findings. Preserve all duplicate locations
and reported metrics; do not invent line numbers or similarity values.
Add parser tests and document the exact command/output format.

**Prompt E --- Hardening** \> Run analysis against the sample fixture.
Verify stable IDs, repository-relative paths, ignored directories,
timeout handling, malformed output, tool coverage statuses and cleanup.
Ensure output matches the agreed schema exactly.

## 10. Test Checklist

-   [ ] Valid public GitHub URL accepted.
-   [ ] Invalid host/scheme/credentials rejected.
-   [ ] Default and explicit branch handled.
-   [ ] Commit metadata captured.
-   [ ] File/byte/time limits enforced.
-   [ ] No target code or package scripts executed.
-   [ ] Knip returns parsed unused-code findings.
-   [ ] jscpd returns parsed duplicate findings.
-   [ ] Paths are repository-relative POSIX paths.
-   [ ] Missing locations remain null.
-   [ ] Failed tools are not represented as zero findings.
-   [ ] Timeout and malformed JSON are handled.
-   [ ] Temporary workspace cleanup works.
-   [ ] Output matches shared Finding schema.

## 11. Handoff

Give TANUJA_4 and SAMAR_3 the function signatures, sample JSON, exact
tool versions/commands, coverage statuses, limitations, required
environment variables and test command/results.

**Final deliverable:** a tested, importable service returning real Knip
and jscpd findings from a safely retrieved public repository.
