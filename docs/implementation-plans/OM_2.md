# OM_2 --- Detailed Static Code Analysis Implementation Plan

**Owner:** OM_2\
**Timebox:** 4 hours (240 minutes)\
**Development approach:** Vibe coding with Antigravity + Gemini 3.8
Flash (Medium)\
**Product:** CodeImpact --- Evidence-Based Codebase Intelligence & Safe
Refactoring\
**Stack:** Python service adapter, Git/GitHub retrieval, Node.js
tooling, Knip, jscpd\
**Deliverable:** An importable analysis module that retrieves an
accessible public GitHub repository, runs real static-analysis tools,
and returns normalised findings to the shared backend.

------------------------------------------------------------------------

## 1. Mission

You own the **repository retrieval and static code analysis layer** of
CodeImpact.

Your task is to take a public GitHub repository and produce
evidence-backed findings for:

-   Potentially unused files.
-   Potentially unused exports.
-   Potentially unused dependencies.
-   Duplicate code blocks.

The output must be predictable JSON that SAMAR_3 can enrich with
dependency/impact information and TANUJA_4 can expose through FastAPI.

You are **not** responsible for frontend development, a second FastAPI
server, AI explanations, final review-risk scoring, dependency-cycle
detection, code deletion, or proving that code is safe to delete.

### Core engineering principle

**A static analyser reports what it could establish from its configured
scan. It does not prove the absence of runtime use.**

Use wording such as "potentially unused" or "no static reference found
by the configured scan". Never label code "safe to delete".

------------------------------------------------------------------------

## 2. Four-Hour Definition of Done

At the end of the timebox:

1.  Accept a public GitHub HTTPS repository URL and optional branch.
2.  Validate the URL on the backend.
3.  Retrieve the selected/default branch into an isolated temporary
    workspace.
4.  Capture repository name, branch, commit SHA, eligible file count,
    and detected languages.
5.  Identify whether a supported JavaScript/TypeScript project exists.
6.  Run Knip using a pinned tool version.
7.  Parse Knip JSON into normalised findings.
8.  Run jscpd and parse its JSON report into duplicate-code findings.
9.  Preserve file paths and line ranges only when actually reported.
10. Return stable finding IDs, source-tool metadata, and per-tool
    coverage.
11. Return partial results when one tool fails.
12. Expose importable functions to TANUJA_4 and SAMAR_3.
13. Pass a prepared fixture-repository test.
14. Commit and hand off the exact contract, tool versions, commands, and
    limitations.

**Acceptance target:** The prepared fixture should produce at least one
real unused-code finding from Knip and one real duplicate-code finding
from jscpd. If a category does not produce a result under the tested
configuration, document the reason; never fabricate output.

------------------------------------------------------------------------

## 3. Team Architecture and Ownership

``` text
                         BHOOMI_1
                    React Frontend / UI
                            |
                            v
                         TANUJA_4
                  FastAPI / Orchestration
                            |
              +-------------+-------------+
              |                           |
              v                           v
            OM_2                        SAMAR_3
    Repository + Static Analysis    Dependency + Impact
              |                           |
              v                           v
       Knip + jscpd                  Madge + Graph
              |                           |
              +-------------+-------------+
                            |
                            v
                 Normalised Analysis Result
```

  -----------------------------------------------------------------------
  Area                    Owner                   OM_2 responsibility
  ----------------------- ----------------------- -----------------------
  GitHub retrieval        OM_2                    Retrieve repository and
                                                  metadata

  Knip                    OM_2                    Run, parse, normalise

  jscpd                   OM_2                    Run, parse, normalise

  Madge/cycles            SAMAR_3                 Provide same workspace

  Review-risk scoring     SAMAR_3                 Leave final risk as
                                                  unknown

  FastAPI/orchestration   TANUJA_4                Provide callable
                                                  services and stable
                                                  schema

  Dashboard               BHOOMI_1                Provide clean JSON and
                                                  field documentation
  -----------------------------------------------------------------------

### First 10 minutes --- contract lock

Agree with TANUJA_4 and SAMAR_3:

-   Exact module paths and function signatures.
-   Which component owns repository workspace cleanup.
-   Whether both analysis modules use the same workspace.
-   Finding category names.
-   `null` semantics for missing line locations.
-   Tool coverage format.
-   How partial analysis is represented.

Do not create duplicate clones if the orchestrator can pass one
workspace to both OM_2 and SAMAR_3.

------------------------------------------------------------------------

## 4. Service Interfaces

Keep this module importable and independent of API routers.

### 4.1 Repository retrieval

``` python
def retrieve_repository(
    repository_url: str,
    branch: str | None = None,
    analysis_id: str | None = None,
) -> dict:
    # Returns internal workspace path and repository metadata.
    ...
```

### 4.2 Static analysis

``` python
def analyze_repository(
    repo_path: str,
    analysis_id: str,
) -> dict:
    # Runs configured analysers; returns findings and tool coverage.
    ...
```

### 4.3 Workspace cleanup helper

``` python
def cleanup_repository_workspace(workspace_path: str) -> None:
    # Called only after SAMAR_3 and report processing no longer need the files.
    ...
```

**Workspace ownership rule:** If TANUJA_4 owns lifecycle, OM_2 must not
delete the directory immediately after its own scan. SAMAR_3 may still
need it.

------------------------------------------------------------------------

## 5. Shared Input and Output Contracts

### 5.1 Retrieval request

``` json
{
  "repository_url": "https://github.com/owner/repository",
  "branch": "main",
  "analysis_id": "an_123"
}
```

### 5.2 Retrieval result

``` json
{
  "workspace_path": "/tmp/codeimpact/an_123",
  "repository": "owner/repository",
  "branch": "main",
  "commit_sha": "abc123",
  "file_count": 120,
  "languages": ["TypeScript", "JavaScript"],
  "status": "retrieved",
  "warnings": []
}
```

`workspace_path` is internal. It must never be sent to the browser.

### 5.3 Normalised finding

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
      "details": "No direct static reference was returned by this configured scan."
    }
  ],
  "risk_factors": [],
  "metadata": {}
}
```

### 5.4 Field rules

  -----------------------------------------------------------------------
  Field                               Rule
  ----------------------------------- -----------------------------------
  `finding_id`                        Stable within an analysis; derive
                                      from analysis ID and finding
                                      identity

  `category`                          Use agreed values only

  `title`                             Human-readable and neutral

  `file_path`                         Repository-relative POSIX path

  `start_line` / `end_line`           Integer only when tool reports a
                                      reliable location; otherwise `null`

  `symbol`                            Symbol only when provided;
                                      otherwise `null`

  `source_tool`                       `knip` or `jscpd`

  `description`                       Describe tool observation without
                                      overstating certainty

  `evidence_class`                    `strong`, `inconclusive`, or
                                      `contradictory`

  `review_risk`                       Always `unknown` at this stage;
                                      SAMAR_3 calculates it

  `evidence`                          Preserve source and status

  `risk_factors`                      Empty list at this stage

  `metadata`                          Tool-specific details such as
                                      duplicate locations and reported
                                      metrics
  -----------------------------------------------------------------------

### 5.5 Agreed categories

-   `unused_file`
-   `unused_export`
-   `unused_dependency`
-   `duplicate_code`
-   `other`

Do not add a category without notifying TANUJA_4 and BHOOMI_1.

### 5.6 Tool coverage

``` json
{
  "tool_coverage": {
    "knip": {
      "status": "completed",
      "finding_count": 7,
      "message": null
    },
    "jscpd": {
      "status": "partial",
      "finding_count": 2,
      "message": "Some files were skipped by the configured scan."
    }
  }
}
```

Allowed status values: `completed`, `partial`, `failed`, `skipped`.

**A failed tool is not equivalent to zero findings.** Only a valid
completed report with an empty result can mean zero findings.

------------------------------------------------------------------------

## 6. Repository Retrieval --- Implementation Detail

### 6.1 Accepted inputs

-   HTTPS URL hosted on `github.com`.
-   Public repository for the MVP.
-   Optional branch.
-   Default branch if branch is omitted.

### 6.2 URL validation

Use a proper URL parser. Require HTTPS and hostname exactly `github.com`
(case-normalised). Reject:

-   Other hosts or schemes.
-   Embedded username/password credentials.
-   Malformed owner/repository paths.
-   Path traversal or unexpected URL path components.
-   Arbitrary clone URLs supplied by the user.

Normalize a trailing slash and `.git` suffix only if supported. Do not
log the full untrusted URL when it may contain sensitive data.

### 6.3 Retrieval method

Use a shallow clone if Git is installed in the backend environment;
GitHub API archive/tree retrieval is an alternative if clone is not
available.

Illustrative command:

``` bash
git clone --depth 1 --no-tags --single-branch --branch main \
  https://github.com/owner/repository.git \
  /tmp/codeimpact/an_123
```

**Implementation requirements:** - Invoke Git with an argument list and
`shell=False`. - Set explicit `cwd`, timeout, and destination. - Do not
build one shell command string. - Do not accept arbitrary local paths
from the client. - Verify that the destination is inside the configured
workspace root. - Inspect process result and checked-out metadata before
marking retrieval successful.

### 6.4 Metadata capture

After retrieval: - Repository full name. - Actual branch/selected ref. -
Commit SHA. - Eligible file count. - Detected language extensions. -
Presence of `package.json`. - TypeScript indicators (`tsconfig.json`,
`.ts` or `.tsx` files). - Warnings about unsupported/ambiguous project
structures.

### 6.5 Workspace layout

``` text
/tmp/codeimpact/
  an_123/
    repository source files...
    .codeimpact/
      reports/
        knip.json
        jscpd/
          jscpd-report.json
```

Generated reports must live in a directory excluded from the scan.

### 6.6 Excluded directories

At minimum:

``` text
.git/
node_modules/
dist/
build/
coverage/
.next/
.nuxt/
.cache/
vendor/
.venv/
__pycache__/
```

Also exclude binary/media files, minified bundles and generated files
when identifiable. Retain package manifests and relevant project
configuration as needed.

### 6.7 Initial resource limits

Make these configurable:

  Limit                                Initial value
  -------------------------- -----------------------
  Clone timeout                           45 seconds
  Maximum eligible files                       5,000
  Maximum single text file                      1 MB
  Per-analyser timeout                    60 seconds
  Total analysis timeout        Agreed with TANUJA_4
  Tool report output cap       Configurable, bounded

These are hackathon defaults, not production guarantees.

### 6.8 Safety and custom configuration

Repository source and configuration are untrusted.

-   Do not execute repository source.
-   Do not run `npm install`, `npm ci`, build scripts, tests, or
    lifecycle scripts.
-   Avoid following symlinks outside the workspace.
-   Use temporary unique directories.
-   Do not load arbitrary dynamic project configuration or plugins
    without isolation.
-   Prefer built-in tool behaviour and non-executable configuration.
-   If an analyser would need to execute untrusted JavaScript/TypeScript
    configuration, either run it in an appropriately restricted
    environment or mark that part `partial`/`skipped`.
-   Keep the workspace until SAMAR_3 and TANUJA_4 confirm downstream
    processing is complete.

------------------------------------------------------------------------

## 7. Safe Subprocess Runner

Build one reusable helper for Git, Knip, and jscpd.

### Required behaviour

-   Argument list only.
-   `shell=False`.
-   Explicit working directory.
-   Timeout.
-   Captured stdout/stderr with limits.
-   Exit code and elapsed time.
-   Structured errors for missing executable, timeout, non-zero exit,
    malformed output.
-   Sanitised logs; no secrets or raw output in client response.

### Internal result

``` json
{
  "command_name": "knip",
  "return_code": 1,
  "stdout": "...",
  "stderr": "...",
  "timed_out": false,
  "duration_ms": 1200,
  "output_truncated": false
}
```

### Exit-code handling

Do not assume non-zero exit always means the analysis crashed. Some
analysis tools use exit codes to indicate findings or thresholds.

Determine the pinned version's behaviour. Consider a run successful
when: - It completed before timeout. - The expected report exists or
valid JSON was emitted. - The report schema parses correctly. - Tool
output indicates analysis completed.

Mark it failed when the executable is unavailable, a timeout occurs,
report generation fails, output is malformed, or the tool crashes before
valid results are produced.

------------------------------------------------------------------------

## 8. Knip Integration --- Potentially Unused Code

### 8.1 Purpose

Use Knip for: - Potentially unused files. - Potentially unused
exports. - Potentially unused dependencies. - Other supported issue
types only if agreed.

Knip builds a project/module graph from entry points and project files.
Its findings depend on correct entry/project configuration. It does not
prove that runtime-generated or external use does not exist.

### 8.2 Tool installation

Pin Knip in CodeImpact's trusted tooling environment, not by installing
dependencies inside the target repository.

Example trusted tool workspace:

``` bash
npm init -y
npm install --save-exact knip
```

Commit the lockfile and use the local executable. Do not use an unpinned
`npx knip@latest` in the final demo.

### 8.3 JSON output

The current Knip CLI documentation supports JSON reporter output and
writing reporter output to a file. A command pattern to test with the
pinned version is:

``` bash
knip --no-progress --reporter json \
  --output-file json=.codeimpact/reports/knip.json
```

Verify the exact option syntax with `knip --help` and the official CLI
reference for the pinned version before hardcoding it. Do not write a
parser based on an assumed report shape.

### 8.4 Knip execution sequence

1.  Confirm `package.json` and supported JS/TS source.
2.  Inspect project manifests and entry-point indicators.
3.  Detect existing Knip configuration.
4.  Identify whether configuration is JSON or executable JS/TS.
5.  Apply the safety policy for executable configuration in Section 6.8.
6.  Run the pinned Knip version with JSON reporter and no-progress mode.
7.  Save the report under `.codeimpact/reports/`.
8.  Parse the report and preserve source metadata.
9.  Map supported issue types to CodeImpact categories.
10. Record project/configuration warnings in `tool_coverage.knip`.

### 8.5 Issue mapping

  -----------------------------------------------------------------------
  Knip issue              CodeImpact category     Display title
  ----------------------- ----------------------- -----------------------
  Unused file             `unused_file`           Potentially unused file

  Unused export           `unused_export`         Potentially unused
                                                  export

  Unused dependency       `unused_dependency`     Potentially unused
                                                  dependency

  Other agreed issue      `other`                 Static analysis finding
  -----------------------------------------------------------------------

Preserve the exact Knip issue type in `metadata.knip_issue_type`. Do not
call every issue "dead code".

### 8.6 Parser rules

-   Inspect a real JSON report from the pinned version first.
-   Parse JSON into a typed internal representation.
-   Preserve path, symbol, issue type and message where available.
-   Only populate line/column when actually reported.
-   Set missing line values to `null`.
-   Resolve relative paths against the repository root.
-   Normalize separators to `/`.
-   Reject paths resolving outside the repository.
-   Handle empty-but-valid report separately from missing/malformed
    report.
-   Keep tool warnings/configuration hints in coverage metadata.

### 8.7 Configuration and false-positive risks

Unexpected unused-file findings can arise from: - Missing or inaccurate
entry-point patterns. - Dynamic import specifiers. - Framework-specific
routes or conventions. - Generated files. - Plugin registration. -
Custom file extensions. - Workspace/monorepo structure. - External
consumers of library exports.

Do not silence findings blindly or create a broad configuration assuming
every file under `src/**` is a normal project file. If project
configuration is incomplete, report the limitation.

### 8.8 Fixture repository

Create a small fixture:

``` text
sample-js-repo/
  package.json
  tsconfig.json
  src/
    index.ts
    app.ts
    utils/
      used.ts
      unused.ts
```

Example `src/index.ts`:

``` typescript
import { greet } from "./app";
console.log(greet("CodeImpact"));
```

Example `src/app.ts`:

``` typescript
export function greet(name: string) {
  return `Hello ${name}`;
}
```

Example `src/utils/unused.ts`:

``` typescript
export function legacyFormatter(value: string) {
  return value.trim().toUpperCase();
}
```

Add the fixture's entry/project configuration intentionally. Run the
pinned version and record its actual expected result. Do not assume all
Knip versions/configurations report the same fixture without validation.

------------------------------------------------------------------------

## 9. jscpd Integration --- Duplicate Code

### 9.1 Purpose

Use jscpd to find repeated code fragments and preserve both locations.
Duplicate detection does not prove that two blocks are semantically
interchangeable.

### 9.2 Tool installation

Install and pin jscpd in the trusted CodeImpact tooling environment:

``` bash
npm install --save-exact jscpd
```

Commit the lockfile and use its local executable.

### 9.3 JSON reporter

The current jscpd documentation describes the JSON report as
containing: - `duplicates`: clone records and their locations. -
`statistics`: counts/statistics per format and in total. - `boundaries`:
optional data when boundary rules are configured.

A documented command pattern is:

``` bash
jscpd . -r json --output .codeimpact/reports/jscpd
```

Verify exact file name and report structure from the pinned version
before implementing the parser.

### 9.4 Execution sequence

1.  Build include/exclude settings for supported JS/TS files.
2.  Exclude generated, dependency, build, coverage and report
    directories.
3.  Run pinned jscpd from repository root.
4.  Save JSON under `.codeimpact/reports/jscpd`.
5.  Confirm the report exists.
6.  Parse duplicate records and statistics.
7.  Normalize both source locations.
8.  Produce a stable finding for each duplicate pair.
9.  Preserve token count, kind, and statistics only if reported.
10. Record skipped-file information and tool status.

### 9.5 Recommended finding convention

Use **one finding per duplicate pair** so the UI can display two clear
locations.

``` json
{
  "finding_id": "f_dup_01",
  "category": "duplicate_code",
  "title": "Duplicate code block",
  "file_path": "src/a.ts",
  "start_line": 20,
  "end_line": 35,
  "symbol": null,
  "source_tool": "jscpd",
  "description": "A matching code block was reported in another file.",
  "evidence_class": "strong",
  "review_risk": "unknown",
  "evidence": [
    {
      "kind": "duplicate_block",
      "status": "found",
      "source": "jscpd",
      "details": "Matching block reported in src/b.ts."
    }
  ],
  "risk_factors": [],
  "metadata": {
    "duplicate_locations": [
      {"file_path": "src/b.ts", "start_line": 8, "end_line": 23}
    ],
    "tokens": 45,
    "kind": "clone"
  }
}
```

Only include values that jscpd actually reports. Do not invent a
similarity percentage. `evidence_class: strong` means the tool returned
a duplicate/clone record; it does not mean the code can automatically be
merged.

### 9.6 Parser rules

-   Build fixture tests from actual JSON emitted by the pinned version.
-   Preserve both file paths and line ranges.
-   Normalize to repository-relative POSIX paths.
-   Verify paths remain inside repository root.
-   Preserve available tokens/kind/statistics.
-   Do not return large raw code fragments in the API by default.
-   Empty `duplicates` array means zero duplicates only if the report is
    valid and the run completed.

------------------------------------------------------------------------

## 10. Normalisation and Stable Finding IDs

### 10.1 Pipeline

``` text
Knip JSON -> parser -> Knip category mapper --+
                                                |
                                                v
                                           Normaliser
                                                |
jscpd JSON -> parser -> duplicate mapper -------+
                                                |
                                                v
                                     Stable finding IDs
                                                |
                                                v
                                   findings + tool coverage
```

### 10.2 Path normalization

For every tool path: 1. Resolve it against repository root. 2. Normalize
to a canonical path. 3. Ensure it remains within repository root. 4.
Convert to relative path. 5. Replace `\` with `/`. 6. Remove unnecessary
`./`. 7. Preserve case.

Reject paths outside the repository.

### 10.3 Stable finding ID

Build a canonical identity string:

``` text
analysis_id | source_tool | category | file_path | symbol | start_line | duplicate_target_path
```

Hash it (for example SHA-256) and use a short prefix. This avoids
duplicate findings when the same report is normalised again.

### 10.4 Deduplication

-   Knip: deduplicate by tool, category, path, symbol and location.
-   jscpd: preserve distinct duplicate pairs; do not collapse different
    pairs merely because one file is shared.
-   Do not merge findings from Knip and jscpd solely because they
    reference the same file.
-   Preserve source-tool identity.

### 10.5 Evidence semantics

-   `found`: tool directly reported a condition (e.g. duplicate block).
-   `not_found`: configured scan did not identify a reference.
-   `unknown`: the system cannot determine the value.
-   `not_checked`: corresponding check did not run.
-   `conflicting`: sources disagree.

For an unused export, overall evidence should normally remain
`inconclusive`; the tool reports no known static reference, not proof of
no runtime use.

------------------------------------------------------------------------

## 11. Tool Coverage and Partial Failure

### 11.1 Expected coverage object

``` json
{
  "tool_coverage": {
    "knip": {
      "status": "completed",
      "finding_count": 7,
      "message": null,
      "duration_ms": 1400
    },
    "jscpd": {
      "status": "failed",
      "finding_count": 0,
      "message": "The analyser did not produce a valid JSON report.",
      "duration_ms": 800
    }
  }
}
```

`duration_ms` is optional.

### 11.2 Required behaviour

  Situation                              Result
  -------------------------------------- ---------------------------------------
  Both tools complete with findings      Return both sets, completed
  Both tools complete with no findings   Return empty list, completed
  Knip succeeds, jscpd fails             Preserve Knip findings, partial
  jscpd succeeds, Knip fails             Preserve jscpd findings, partial
  Unsupported project                    Mark relevant tool skipped
  Timeout                                Mark tool failed with timeout message
  Missing executable                     Mark tool failed
  Malformed JSON                         Mark tool failed
  Report absent                          Mark tool failed

The overall analysis status is coordinated with TANUJA_4. Do not create
a competing top-level status enum.

------------------------------------------------------------------------

## 12. Project Structure

Adapt to the existing repository; do not move existing files
unnecessarily.

``` text
backend/
  app/
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
      tool_coverage.py
    utils/
      file_filter.py
      path_safety.py
  tests/
    fixtures/
      sample_js_repo/
      knip_reports/
      jscpd_reports/
    test_repository_retrieval.py
    test_safe_subprocess.py
    test_knip_parser.py
    test_jscpd_parser.py
    test_finding_normalizer.py
```

  Module                         Responsibility
  ------------------------------ --------------------------------------------
  `repository_retrieval.py`      URL validation, retrieval and metadata
  `safe_subprocess.py`           Safe command execution
  `knip_runner.py`               Run Knip and parse its report
  `jscpd_runner.py`              Run jscpd and parse its report
  `file_filter.py`               Excluded paths and eligible-file inventory
  `path_safety.py`               Repository-relative path validation
  `output_normalizer.py`         Categories, IDs, evidence and common shape
  `static_analysis_service.py`   Run tools and aggregate results

------------------------------------------------------------------------

## 13. Four-Hour Schedule --- Minute by Minute

  -------------------------------------------------------------------------------
  Time                    Activity                        Concrete output
  ----------------------- ------------------------------- -----------------------
  00--15                  Pull latest branch, inspect     Shared interface locked
                          structure, agree signatures and 
                          schemas                         

  15--40                  Implement URL validation,       Public repository
                          shallow retrieval, metadata and retrieved
                          limits                          

  40--60                  Implement safe subprocess       Reusable command
                          runner                          utility

  60--115                 Pin Knip, run fixture, inspect  Unused-code findings
                          JSON, implement parser          

  115--155                Pin jscpd, run fixture, inspect Duplicate-code findings
                          JSON, implement parser          

  155--180                Normalise                       Common JSON output
                          IDs/paths/categories/evidence   
                          and aggregate                   

  180--205                Add timeout, partial/failure,   Robust error handling
                          safety and workspace tests      

  205--225                Integrate with SAMAR_3 and      Callable service in
                          TANUJA_4                        shared app

  225--240                Fixture regression, commit,     Verified module
                          handoff                         
  -------------------------------------------------------------------------------

### Time discipline

-   Do not spend more than 20 minutes debugging a non-essential tool
    option; inspect its CLI help and documented output.
-   If Knip integration takes too long, finish one reliable Knip
    category first, then add the others.
-   jscpd is secondary to obtaining a real unused-code result, but both
    are required for the target deliverable.
-   Do not add ESLint unless required integrations already pass.

------------------------------------------------------------------------

## 14. Antigravity Workflow --- Gemini 3.8 Flash (Medium)

### General instruction to prepend to every prompt

> You are implementing OM_2's CodeImpact Static Code Analysis module.
> Work only in this module and preserve other teammates' changes. First
> inspect the existing repository and shared schemas. Do not create a
> second FastAPI application. Do not fabricate tool output or claim
> tests passed unless you ran them. Implement one stage at a time, run
> relevant tests, and report changed files, commands, actual results,
> limitations and next steps. Ask before changing shared interfaces.

### Prompt 1 --- Repository retrieval

> Implement
> `retrieve_repository(repository_url, branch=None, analysis_id=None)`
> in the existing CodeImpact backend. Accept only public HTTPS GitHub
> repository URLs. Validate host and path, reject embedded credentials,
> retrieve the selected/default branch into a unique temporary
> workspace, and capture repository name, branch, commit SHA, eligible
> file count and detected JS/TS languages. Use Git subprocess with
> argument arrays, shell=False, explicit timeout and destination.
> Enforce file/size/time limits, prevent path traversal and symlink
> escape, do not execute repository source or package scripts, and
> return a structured internal result. Do not create API routes. Add
> tests and show actual output from a sample repository.

### Prompt 2 --- Safe subprocess runner

> Implement a reusable subprocess runner for trusted CodeImpact analyzer
> executables. Require argument arrays, shell=False, explicit working
> directory, timeout, bounded stdout/stderr, exit code, duration and
> structured errors. Never interpolate repository input into shell
> commands. Add tests for success, timeout, missing executable, non-zero
> exit and output truncation. Do not change teammate-facing function
> signatures.

### Prompt 3 --- Knip

> Integrate a pinned Knip version in CodeImpact's trusted tool
> environment. Use the pinned version's documented JSON reporter and
> output-file option. First run it on the fixture and save the actual
> report as a parser fixture. Parse unused files, exports and
> dependencies into the shared Finding schema. Preserve paths, symbols
> and source metadata; use null for unavailable line numbers. Detect
> executable custom-config risk and do not blindly execute untrusted
> JS/TS config or package scripts. Mark incomplete scans partial. Add
> parser tests.

### Prompt 4 --- jscpd

> Integrate pinned jscpd in CodeImpact's trusted tool environment. Use
> its documented JSON reporter and output directory. First run it on the
> fixture and inspect the real report structure. Parse duplicate records
> and statistics. Produce a stable finding per duplicate pair, retain
> both file locations and reported line ranges, and store available
> token/kind statistics in metadata. Do not invent similarity
> percentages. Exclude generated, dependency and report folders. Add
> fixture parser tests.

### Prompt 5 --- Normalisation and service

> Implement `analyze_repository(repo_path, analysis_id)` to run Knip and
> jscpd, normalise output and return findings plus tool_coverage.
> Generate stable finding IDs, repository-relative POSIX paths, nullable
> line values, agreed categories, source tool, evidence and metadata.
> Keep review_risk as unknown because SAMAR_3 owns impact/risk. Tool
> failure must not be represented as successful zero findings. Add tests
> for completed, partial, failed and skipped states. Keep this as an
> importable service, not an API route.

### Prompt 6 --- Integration audit

> Run the full analyzer against the prepared fixture. Verify expected
> Knip/jscpd results, parser correctness, line/path accuracy, stable
> IDs, exclusions, coverage states, workspace cleanup ownership and
> safety requirements. Confirm no package scripts or target source code
> were executed. Integrate with SAMAR_3 and TANUJA_4 using agreed
> contracts. Report exact commands, tests, changed files and remaining
> limitations. Do not claim success for anything not run.

### How to use Gemini efficiently

-   Give one task at a time.
-   Ask it to inspect files before editing.
-   Review its proposed changes before accepting large rewrites.
-   Run the test/CLI command yourself after each integration.
-   Keep the shared schema in context.
-   Do not ask it to "finish the entire module" in one prompt.
-   If the agent changes unrelated teammates' files, revert only those
    unintended changes after checking with the team.

------------------------------------------------------------------------

## 15. Testing Plan

### 15.1 Repository retrieval tests

-   Valid GitHub HTTPS URL.
-   Trailing slash and `.git` normalisation.
-   Invalid URL.
-   Non-GitHub host.
-   HTTP instead of HTTPS.
-   Embedded credentials.
-   Missing repository.
-   Invalid branch.
-   Clone timeout.
-   Repository over file/size limits.
-   Workspace cleanup.
-   Symlink/path traversal attempt.

### 15.2 Knip parser tests

Use a captured real report from the pinned version. Test: - Unused
file. - Unused export. - Unused dependency. - Multiple findings in one
file. - Missing line/column. - Unknown issue type. - Empty but valid
report. - Malformed JSON. - Configuration warning/partial scan.

### 15.3 jscpd parser tests

Use a captured real report from the pinned version. Test: - One
duplicate pair. - Multiple duplicate pairs. - Same-file duplicate if
tool reports it. - Missing location. - Statistics present/absent. -
Empty but valid report. - Malformed JSON. - Timeout. - Missing report
path.

### 15.4 Integration tests

-   Both tools succeed.
-   Knip succeeds/jscpd fails.
-   jscpd succeeds/Knip fails.
-   Both tools fail.
-   Unsupported project skips tools.
-   Report directory is not scanned.
-   Repeated normalisation yields stable IDs.
-   Workspace remains available for SAMAR_3 until orchestrator cleanup.
-   Output passes the shared schema.

------------------------------------------------------------------------

## 16. Common Failure Modes

  -----------------------------------------------------------------------
  Failure                 Likely cause            Correct response
  ----------------------- ----------------------- -----------------------
  Knip flags too many     Entry/project patterns  Inspect project
  files                   incomplete              structure; record
                                                  limitation

  Knip reports nothing    Wrong working           Verify project
  unexpectedly            directory, unsupported  detection, status and
                          project or incomplete   report
                          execution               

  Knip report missing     Wrong reporter/output   Check pinned CLI help;
                          flag or tool failed     mark failed

  Knip config cannot be   Executable project      Skip or isolate; mark
  loaded safely           config/plugin           partial

  jscpd finds no          Fixture has none or     Verify fixture/config;
  duplicates              thresholds too          do not fake findings
                          restrictive             

  jscpd report shape      Tool version/schema     Pin version and update
  differs                 drift                   parser fixture

  Paths are absolute      Tool outputs workspace  Resolve and normalise
                          paths                   against repository root

  Line number missing     Tool does not provide   Keep null
                          location                

  Non-zero exit           Issues threshold or     Check valid report and
                          actual error            documented exit
                                                  semantics

  Clone stalls            Network, large repo or  Timeout and structured
                          invalid branch          retrieval error

  Node executable missing Backend runtime         Report prerequisite; do
                          incomplete              not auto-install target
                                                  deps

  Reports become scanned  Report directory not    Exclude `.codeimpact/`
  files                   excluded                before tool execution
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 17. Handoff Requirements

### To TANUJA_4

-   `retrieve_repository()` signature and result shape.
-   `analyze_repository()` signature and result shape.
-   Sample normalised JSON.
-   Tool coverage statuses.
-   Exact Knip/jscpd versions and commands.
-   Environment prerequisites (Git, Node.js, Python).
-   Configuration execution limitations.
-   Workspace retention/cleanup ownership.
-   Test commands and actual results.

### To SAMAR_3

-   Shared workspace path contract.
-   Repository name, branch and commit metadata.
-   Normalised findings array.
-   Path convention: repository-relative with `/` separators.
-   Confirmation that OM_2 does not calculate final impact/risk.

### To BHOOMI_1 (through TANUJA_4)

-   Category labels and exact field names.
-   Which line values can be null.
-   Tool coverage statuses.
-   Example unused-export and duplicate-pair findings.

------------------------------------------------------------------------

## 18. Final Checklist

### Retrieval

-   [ ] Public GitHub URL accepted and validated.
-   [ ] Requested/default branch handled.
-   [ ] Commit SHA and repository metadata returned.
-   [ ] File/size/time limits enforced.
-   [ ] Workspace isolated.
-   [ ] No repository scripts or source code executed.

### Knip

-   [ ] Pinned version installed in trusted tool environment.
-   [ ] JSON report generated and inspected.
-   [ ] Unused file/export/dependency mappings tested.
-   [ ] Entry/config limitations captured.
-   [ ] Missing line locations remain null.

### jscpd

-   [ ] Pinned version installed.
-   [ ] JSON report generated and inspected.
-   [ ] Both duplicate locations preserved.
-   [ ] Available statistics preserved.
-   [ ] Generated/dependency/report directories excluded.

### Output and integration

-   [ ] Stable finding IDs.
-   [ ] Repository-relative paths.
-   [ ] Category names match shared contract.
-   [ ] Source tool preserved.
-   [ ] Evidence preserved.
-   [ ] Final risk left to SAMAR_3.
-   [ ] Partial/failed/skipped states accurate.
-   [ ] TANUJA_4 can call the functions.
-   [ ] SAMAR_3 can use the same workspace.
-   [ ] Frontend never receives local filesystem paths.
-   [ ] Fixture flow works and code is committed.

------------------------------------------------------------------------

## 19. Official Tool References

Check the exact documentation for the pinned tool version before
finalising commands and parsers:

-   [Knip CLI arguments](https://knip.dev/reference/cli) --- reporter
    selection, output file, include/exclude options and execution modes.
-   [Knip configuration](https://knip.dev/reference/configuration) ---
    project/entry patterns and configuration controls.
-   [Knip handling reported
    issues](https://knip.dev/guides/handling-issues) --- why
    unused-file/export findings depend on project configuration and
    entry points.
-   [jscpd CLI options](https://jscpd.dev/reference/cli) --- reporters
    and output directory.
-   [jscpd JSON reporter](https://jscpd.dev/reference/reporters/json)
    --- duplicate records and statistics structure.

The current documentation supports Knip JSON reporting to a file and
jscpd's JSON reporter output. Pin the versions used by CodeImpact and
create parser fixtures from their actual reports; do not assume report
schemas remain identical across versions.

------------------------------------------------------------------------

## 20. Final Deliverable

OM_2 is complete when CodeImpact can safely retrieve a supported public
GitHub repository, run pinned Knip and jscpd analysis, and return
accurate, normalised, traceable findings with per-tool coverage. SAMAR_3
must be able to use the same repository workspace, TANUJA_4 must
orchestrate the module through a stable service interface, and BHOOMI_1
must display the results without guessing missing fields.

**Success is real findings and honest limitations --- not the largest
number of warnings.**
