# Product Requirements Document (PRD)

## CodeImpact --- Evidence-Based Codebase Intelligence & Safe Refactoring

**Document status:** Hackathon MVP specification\
**Version:** 1.0\
**Product category:** Developer Productivity / Static Analysis /
AI-Assisted Refactoring\
**Target build time:** 4--5 hours\
**Primary users:** Software developers, engineering teams, technical
leads and maintainers

------------------------------------------------------------------------

## 1. Executive Summary

CodeImpact is a codebase intelligence platform that helps developers
identify potential technical debt and make better-informed cleanup
decisions.

It analyses a GitHub repository using established static-analysis tools,
combines findings with dependency and available test-coverage evidence,
estimates the risk and potential impact of proposed cleanup, and uses an
LLM to explain findings and suggest developer-reviewed changes.

CodeImpact is not intended to replace linters, static-analysis engines
or code-review platforms. Its value is in connecting their findings into
one evidence-based workflow:

**Analyse → Verify → Assess impact → Recommend → Review → Validate**

The central product promise is:

> Don't just find potentially unused code. Understand the evidence,
> dependencies and risks before changing it.

------------------------------------------------------------------------

## 2. Problem Statement

As software repositories evolve, they accumulate technical debt such as:

-   Functions, exports, variables and imports that may no longer be
    used.
-   Files that appear disconnected from known application entry points.
-   Repeated or near-duplicate code.
-   Circular dependencies and highly coupled modules.
-   Unreachable code and redundant abstractions.
-   Incomplete or poorly understood test coverage around code changes.

Existing tools can detect many of these issues. However, developers may
still need to combine results from multiple tools and manually determine
whether a finding is safe to act on.

A static-analysis tool may report that a function has no direct
references, but the function could still be invoked through dynamic
imports, reflection, plugin registration, framework conventions,
configuration or an external consumer. A finding should therefore not be
presented as proof that code is safe to delete.

### Core user problem

Developers need a unified way to understand:

1.  What code may be unnecessary?
2.  What evidence supports that finding?
3.  What dependencies or tests may be affected?
4.  What is the potential risk of changing it?
5.  What cleanup action should be considered next?

------------------------------------------------------------------------

## 3. Product Vision

Build a practical developer tool that transforms fragmented
code-analysis findings into prioritised, explainable and reviewable
cleanup decisions.

### Product positioning

**CodeImpact is an evidence-based codebase intelligence and
safe-refactoring assistant.**

### Value proposition

CodeImpact analyses a repository, identifies potential technical debt,
explains why components were flagged, maps relevant dependencies,
estimates cleanup risk and proposes changes for developer review.

### Differentiation principles

1.  **Evidence over assumptions:** Every finding should show its source
    and limitations.
2.  **Impact before action:** Show dependencies and available test
    evidence before suggesting removal.
3.  **Human approval:** Never silently delete code or commit changes to
    the user's branch.
4.  **Deterministic detection, AI explanation:** Static-analysis tools
    establish findings; AI explains and helps remediate them.
5.  **Transparent scoring:** Risk and confidence scores must be based on
    documented heuristics, not invented by the LLM.

------------------------------------------------------------------------

## 4. Goals and Non-Goals

### 4.1 Product goals

-   Allow a user to analyse a supported GitHub repository.
-   Identify selected categories of potential technical debt.
-   Consolidate findings from established analysis tools.
-   Visualise file-level dependencies and circular dependencies.
-   Present evidence, confidence and risk for each finding.
-   Estimate which files and tests may be affected by a proposed
    cleanup.
-   Generate concise AI explanations and suggested remediation.
-   Produce a downloadable analysis report.
-   Deliver a reliable, demonstrable MVP within 4--5 hours.

### 4.2 Non-goals for the hackathon MVP

-   Supporting every programming language.
-   Proving that code is universally safe to delete.
-   Building a proprietary compiler or AST engine.
-   Training a custom AI model.
-   Full production-grade runtime tracing.
-   Complete test impact analysis across all build systems.
-   Automatic modification of the user's default branch.
-   Production-grade multi-tenant authentication and billing.
-   Guaranteed performance improvement estimates.
-   Full CI/CD, IDE or enterprise integrations.

------------------------------------------------------------------------

## 5. Target Users and Use Cases

### Primary personas

**Persona A --- Software Developer** - Wants to understand whether a
function or file is still used. - Needs to reduce clutter before adding
or modifying features. - Wants evidence and a clear explanation rather
than a raw warning.

**Persona B --- Tech Lead / Engineering Manager** - Wants visibility
into repository maintainability. - Needs to prioritise technical-debt
work. - Wants a summary that can be shared with the team.

**Persona C --- Open-Source Maintainer** - Maintains a growing
repository. - Wants to identify stale modules and duplicated logic. -
Needs cleanup suggestions that contributors can review.

### Core user stories

1.  As a developer, I want to enter a repository URL so I can analyse a
    codebase without manually uploading every file.
2.  As a developer, I want to see unused-code candidates with file paths
    and line numbers so I can inspect the exact finding.
3.  As a developer, I want to see why a component was flagged so I can
    judge whether the result is trustworthy.
4.  As a developer, I want to view dependency relationships so I can
    understand what may be affected by a change.
5.  As a developer, I want to see related test files and available
    coverage evidence so I can validate a cleanup.
6.  As a developer, I want an understandable risk assessment so I can
    prioritise review.
7.  As a developer, I want AI to explain findings and propose a patch,
    while retaining control over whether to apply it.
8.  As a team lead, I want a report summarising repository findings and
    recommended next steps.

------------------------------------------------------------------------

## 6. Scope and Functional Requirements

The product is organised into six integrated modules.

### Module 1 --- Repository Intelligence

**Purpose:** Import and establish the structure and metadata of a
repository.

#### Requirements

-   Accept a public GitHub repository URL.
-   Validate the URL and repository accessibility.
-   Support a selected branch where feasible; otherwise use the
    repository's default branch.
-   Retrieve repository metadata and source files.
-   Exclude common generated or irrelevant directories, such as
    `node_modules`, `.git`, build output and cache folders.
-   Detect supported languages and package-manager files.
-   Identify likely source, test, configuration and entry-point files.
-   Display repository name, branch, detected languages, file count and
    scan status.

#### MVP constraints

-   Public repositories only.
-   JavaScript and TypeScript are the primary supported languages.
-   Set file-count, file-size and execution-time limits.
-   Do not execute repository code during repository import or static
    analysis.

#### Acceptance criteria

-   A valid public repository can be submitted and scanned.
-   An invalid or inaccessible repository produces a clear error.
-   The user can see scan progress and a final status.
-   The analysis result identifies the repository and branch analysed.

### Module 2 --- Static Code Analysis

**Purpose:** Detect potential code-quality and technical-debt findings
using existing tools.

#### MVP finding categories

1.  Unused exports and files.
2.  Unused dependencies and imports, where supported by the selected
    analyser and configuration.
3.  Unused variables, where supported by the language analyser.
4.  Duplicate or near-duplicate code blocks.
5.  Circular dependencies.
6.  Potentially orphaned files.
7.  Unreachable code, where supported by the selected analyser.

#### Suggested integrations

  Analysis task                                     Suggested tool
  ------------------------------------------------- ----------------
  Unused files, exports and dependencies in JS/TS   Knip
  JavaScript/TypeScript lint findings               ESLint
  Duplicate code blocks                             jscpd
  Dependency graph and cycles                       Madge
  Graph representation and traversal                NetworkX

Tool availability, command-line options and compatibility must be
verified during implementation. The MVP may use a smaller subset if
installation or integration time is limited.

#### Finding data model

Each finding should contain:

-   Unique finding ID.
-   Finding category.
-   Title and short description.
-   File path.
-   Start and end line, when available.
-   Symbol or component name, when available.
-   Detection source/tool.
-   Raw evidence or concise evidence summary.
-   Severity or priority supplied by the tool, if available.
-   Confidence classification.
-   Scan timestamp.

#### Acceptance criteria

-   At least unused-code findings and duplicate-code findings are
    displayed from actual analyser output.
-   Each finding includes a source file or an explicit indication that
    the location is unavailable.
-   Findings are not fabricated by the AI model.
-   The UI distinguishes a confirmed tool result from a CodeImpact
    inference.

### Module 3 --- Dependency Intelligence

**Purpose:** Show how files depend on one another and expose structural
risks.

#### Requirements

-   Build a directed graph where files or modules are nodes and import
    relationships are edges.
-   Identify circular dependency cycles.
-   Identify files with no incoming references in the analysed graph.
-   Display dependency counts for selected files.
-   Highlight cycle members in the visual graph.
-   Allow the user to select a node and inspect its direct
    relationships.

#### MVP implementation

-   Use Madge or equivalent tooling to extract dependency relationships.
-   Use NetworkX for graph processing where useful.
-   Use React Flow for interactive graph visualisation.

#### Important limitation

A file with no incoming edge in the analysed graph is only a **potential
orphan**. It may be an application entry point, dynamically loaded
module, plugin, route, script or externally consumed file.

#### Acceptance criteria

-   The dependency graph is generated from repository analysis output.
-   Circular dependency cycles are identified and shown.
-   Selecting a node displays its connected files.
-   Potential orphan findings include a warning that dynamic and
    external references may not be visible.

### Module 4 --- Evidence, Impact and Risk Assessment

**Purpose:** Help developers understand the strength of a finding and
the possible consequences of acting on it.

This module is the primary differentiator of CodeImpact.

#### Evidence collection

For each selected finding, collect available evidence such as:

-   Direct reference count.
-   Import/export relationships.
-   Incoming and outgoing dependency counts.
-   Whether the component is exported.
-   Whether the file appears to be an entry point.
-   Dynamic-import or reflection indicators, where detectable.
-   Related test-file references.
-   Runtime coverage evidence, if the user supplies a compatible
    coverage report.

#### Evidence classification

  ---------------------------------------------------------------------
  Classification                     Meaning
  ---------------------------------- ----------------------------------
  Strong evidence                    Multiple available signals support
                                     the finding and no known reference
                                     was identified

  Inconclusive                       Some evidence supports the
                                     finding, but important usage paths
                                     cannot be verified

  Contradictory evidence             Available evidence suggests the
                                     component may be used
  ---------------------------------------------------------------------

Avoid describing a component as definitively safe to delete based only
on static analysis.

#### Risk assessment

The MVP should calculate a transparent heuristic score. It must be
labelled as an estimate, not a guarantee.

Potential factors:

-   Detection confidence.
-   Incoming dependency count.
-   Entry-point or exported status.
-   Dynamic-usage indicators.
-   Related test references.
-   Runtime coverage evidence, when supplied.

A simple initial approach:

-   Start from the static analyser's finding confidence or a documented
    rule-based baseline.
-   Increase review risk when a component is an entry point, exported,
    dynamically referenced or has incoming dependencies.
-   Treat missing runtime/test evidence as **unknown**, not as proof of
    no usage.
-   Explain the factors that influenced the resulting classification.

Suggested output:

  ---------------------------------------------------------------------
  Risk label                         Interpretation
  ---------------------------------- ----------------------------------
  Lower review risk                  Available evidence suggests
                                     limited known impact; still
                                     requires developer review

  Medium review risk                 Dependencies or incomplete
                                     evidence require additional
                                     inspection

  Higher review risk                 Known relationships or uncertainty
                                     make removal particularly risky
  ---------------------------------------------------------------------

Do not use a score such as "91% safe to delete" unless it has been
calibrated and validated against labelled examples. Prefer a transparent
risk label and evidence breakdown for the MVP.

#### Acceptance criteria

-   Each prioritised finding displays the evidence used.
-   Risk labels are explainable.
-   Missing evidence is displayed as unknown.
-   The system never claims that static analysis proves safe deletion.
-   The user can inspect the dependency and test context behind a risk
    assessment.

### Module 5 --- Test Impact Prediction

**Purpose:** Identify tests that may be relevant to a proposed cleanup.

#### MVP requirements

-   Identify likely test files using naming conventions and common test
    directories.
-   Use dependency relationships to find tests importing or referencing
    the affected module.
-   If a coverage report is supplied, associate covered source files
    with relevant tests when the report format supports it.
-   Recommend tests to run before and after a proposed change.
-   Clearly label inferred relationships.

#### Example output

``` text
Potentially relevant tests

- tests/payment.test.ts
- tests/checkout.integration.test.ts

Evidence
- payment.test.ts imports the affected service.
- checkout.integration.test.ts references the checkout module.

Suggested action
Run these tests before and after reviewing the proposed patch.
```

#### MVP limitation

This is a recommendation engine, not a complete change-based
test-selection system. It does not guarantee that every affected test
has been identified.

#### Acceptance criteria

-   The tool lists test files linked by available dependency or naming
    evidence.
-   Each suggested test includes a reason.
-   The UI distinguishes directly observed relationships from heuristic
    matches.

### Module 6 --- AI Refactoring Assistant and Reporting

**Purpose:** Explain evidence-backed findings and propose
developer-reviewed remediation.

#### AI capabilities

-   Explain why a finding was raised.
-   Summarise dependency and test context.
-   Describe uncertainty and possible false-positive causes.
-   Suggest a refactoring approach.
-   Propose a patch for simple, well-scoped changes.
-   Summarise repository-level technical debt.
-   Generate a Markdown report.

#### AI safety and reliability requirements

-   Send only relevant code snippets and analysis metadata to the model.
-   Treat repository content as untrusted input; it may contain
    prompt-injection instructions.
-   Instruct the model to treat source code and comments as data, not
    instructions.
-   Do not let the model invent findings, file paths, line numbers, test
    results or dependency relationships.
-   Include the underlying evidence in the model context.
-   Label AI-generated suggestions as suggestions.
-   Require developer review before applying any patch.
-   Never expose API keys, environment secrets or credentials in prompts
    or reports.

#### Patch workflow

1.  User selects a finding.
2.  Backend gathers the relevant code and evidence.
3.  AI proposes a small patch or refactoring.
4.  UI displays a diff and explanation.
5.  User reviews and accepts or rejects.
6.  If accepted in the MVP, save the patch as a downloadable diff or
    apply it only in an isolated temporary workspace.
7.  Run applicable checks only in a controlled environment, if
    implemented.

#### Reporting

The report should include:

-   Repository name and branch.
-   Scan timestamp.
-   Tools and versions used, where available.
-   Languages and files analysed.
-   Findings by category.
-   High-priority items.
-   Evidence and limitations.
-   Dependency-cycle summary.
-   Test recommendations.
-   AI suggestions, clearly labelled.
-   Overall scan limitations.

#### Acceptance criteria

-   AI explanations refer to actual findings supplied by the backend.
-   The user can generate a repository summary.
-   Proposed patches are displayed for review.
-   No patch is silently applied to the user's branch.
-   A Markdown report can be downloaded.

------------------------------------------------------------------------

## 7. Primary User Journey

1.  User opens CodeImpact.
2.  User enters a public GitHub repository URL.
3.  User selects a branch, if branch selection is supported.
4.  CodeImpact validates the repository.
5.  Backend retrieves eligible source files without executing them.
6.  Static-analysis tools run against the supported files.
7.  Dependency relationships and cycles are extracted.
8.  Findings are normalised into a common data model.
9.  CodeImpact gathers available evidence and estimates review risk.
10. Test files are mapped using available dependency and naming
    evidence.
11. User views the repository overview and findings explorer.
12. User selects a finding to inspect its evidence and impact.
13. AI explains the finding and may propose a patch.
14. User reviews the recommendation.
15. User downloads the report or proposed diff.

------------------------------------------------------------------------

## 8. UX and Screen Requirements

### Screen 1 --- Repository Connection

Elements:

-   Product name and short value proposition.
-   GitHub repository URL input.
-   Branch selector, if supported.
-   Analyse button.
-   Recent scans, if implemented.
-   Clear public-repository and size limitations.

### Screen 2 --- Repository Overview

Display:

-   Repository name and branch.
-   Languages detected.
-   Files analysed.
-   Lines of code, only if reliably measured.
-   Findings by category.
-   Circular dependency count.
-   Duplicate-code groups.
-   Scan status and timestamp.

Do not display fabricated metrics or an arbitrary "health score." If a
composite score is included, document its formula and label it as an
internal heuristic.

### Screen 3 --- Findings Explorer

Provide filters for:

-   Potentially unused code.
-   Unused imports/dependencies.
-   Duplicate code.
-   Circular dependencies.
-   Potentially orphaned files.
-   Unreachable code.

Each finding card or row should show:

-   Category and description.
-   File and line location.
-   Detection tool.
-   Evidence summary.
-   Confidence or evidence classification.
-   Review-risk label.
-   Inspect action.

### Screen 4 --- Dependency Visualiser

-   Interactive graph of files and imports.
-   Distinct visual treatment for cycle members.
-   Node selection and details panel.
-   Search or filter by file path, if time permits.
-   Clear legend.

### Screen 5 --- Finding Details / CodeImpact Assistant

Show:

-   Finding summary.
-   Relevant source snippet.
-   Why it was flagged.
-   Evidence collected.
-   Known dependencies.
-   Potentially relevant tests.
-   Limitations and uncertainty.
-   Risk classification.
-   AI explanation.
-   Suggested patch, if generated.

### Screen 6 --- Report

-   Repository summary.
-   Findings grouped by category and priority.
-   Evidence and limitations.
-   Recommendations.
-   Download Markdown report.

For the hackathon, Screens 2--5 may be implemented as tabs within one
dashboard rather than separate routes.

------------------------------------------------------------------------

## 9. Technical Architecture

### High-level architecture

``` text
                  USER
                    |
                    v
             REACT + VITE UI
                    |
                    v
              FASTAPI BACKEND
                    |
                    v
          REPOSITORY CONNECTOR
           (GitHub API / Git)
                    |
                    v
             FILE FILTERING
                    |
                    v
          LANGUAGE / PROJECT DETECTION
                    |
          +---------+----------+
          |         |          |
          v         v          v
        KNIP      JSCPD      MADGE
     Unused code  Duplicate  Dependencies
                  code      and cycles
          |         |          |
          +---------+----------+
                    |
                    v
           FINDING NORMALISER
                    |
                    v
       EVIDENCE & IMPACT ASSESSMENT
                    |
                    v
          TEST IMPACT MAPPING
                    |
                    v
          GEMINI / GEMMA SERVICE
          (explanation and patch)
                    |
                    v
          REPORT / PATCH OUTPUT
                    |
                    v
              REACT DASHBOARD
```

### Suggested technology stack

  -----------------------------------------------------------------------
  Layer                   Technology              Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                React + Vite +          User interface
                          TypeScript              

  Styling                 Tailwind CSS /          UI components
                          shadcn/ui               

  Backend                 Python + FastAPI        API and orchestration

  Repository access       GitHub API or shallow   Retrieve source files
                          clone                   

  Unused-code analysis    Knip                    JS/TS unused files,
                                                  exports and
                                                  dependencies

  Lint analysis           ESLint                  Language-specific lint
                                                  findings

  Duplicate detection     jscpd                   Repeated code blocks

  Dependency analysis     Madge                   Dependency graph and
                                                  cycles

  Graph processing        NetworkX                Graph queries and
                                                  analysis

  Graph UI                React Flow              Interactive dependency
                                                  graph

  AI                      Gemini or Gemma API     Explanations and patch
                                                  proposals

  Report                  Markdown generation     Downloadable report
  -----------------------------------------------------------------------

Tool versions and integration commands should be checked during setup.
Avoid spending hackathon time integrating every tool if a core tool is
unavailable.

### Backend API outline

  ---------------------------------------------------------------------------------------
  Method           Endpoint                                              Purpose
  ---------------- ----------------------------------------------------- ----------------
  POST             `/api/repositories/analyse`                           Start repository
                                                                         analysis

  GET              `/api/analyses/{analysis_id}`                         Get scan status
                                                                         and summary

  GET              `/api/analyses/{analysis_id}/findings`                Retrieve
                                                                         findings

  GET              `/api/analyses/{analysis_id}/graph`                   Retrieve
                                                                         dependency graph

  GET              `/api/analyses/{analysis_id}/findings/{finding_id}`   Retrieve finding
                                                                         evidence

  POST             `/api/analyses/{analysis_id}/explain`                 Generate AI
                                                                         explanation

  POST             `/api/analyses/{analysis_id}/patch`                   Generate
                                                                         proposed patch

  GET              `/api/analyses/{analysis_id}/report`                  Download
                                                                         Markdown report
  ---------------------------------------------------------------------------------------

The API can be simplified for the MVP. A single analysis endpoint
returning a complete result is acceptable if it reduces implementation
time.

------------------------------------------------------------------------

## 10. Data Model

### Analysis

``` json
{
  "analysis_id": "analysis_001",
  "repository": "owner/repository",
  "branch": "main",
  "status": "completed",
  "languages": ["JavaScript", "TypeScript"],
  "files_analysed": 120,
  "created_at": "ISO-8601 timestamp"
}
```

### Finding

``` json
{
  "finding_id": "finding_001",
  "category": "potentially_unused_export",
  "title": "Potentially unused export",
  "symbol": "calculateDiscount",
  "file_path": "src/utils/pricing.ts",
  "start_line": 12,
  "end_line": 16,
  "source_tool": "knip",
  "evidence": {
    "direct_references": 0,
    "is_entry_point": false,
    "dynamic_usage_check": "inconclusive"
  },
  "evidence_classification": "inconclusive",
  "review_risk": "medium"
}
```

### Dependency edge

``` json
{
  "source": "src/App.tsx",
  "target": "src/services/auth.ts",
  "relationship": "imports"
}
```

### Patch proposal

``` json
{
  "patch_id": "patch_001",
  "finding_id": "finding_001",
  "status": "proposed",
  "diff": "unified diff content",
  "explanation": "Proposed change explanation",
  "validation_status": "not_run"
}
```

All values must be populated from actual analysis or explicitly marked
unknown. These examples are schemas, not expected scan results.

------------------------------------------------------------------------

## 11. Non-Functional Requirements

### Performance

-   Provide clear scan progress.
-   Apply repository file-count and file-size limits.
-   Avoid loading the entire repository into browser memory.
-   Run analysis tasks asynchronously if necessary.
-   Fail gracefully when an analyser times out.

### Security

-   Do not execute untrusted repository code as part of static analysis.
-   Treat repository source, comments, README files and configuration as
    untrusted data.
-   Do not log GitHub tokens, model API keys or environment secrets.
-   Use least-privilege access.
-   Prefer public repositories for the hackathon MVP.
-   If cloning repositories, use isolated temporary directories and
    clean them after analysis.
-   Do not run package installation scripts from untrusted repositories.
-   Do not execute generated patches against a production environment.
-   Set request timeouts and resource limits.

### Reliability

-   Preserve the original tool output for traceability.
-   Handle unsupported files without failing the entire scan.
-   Distinguish scan failure from zero findings.
-   Show partial results if one analyser fails.
-   Include analyser names and versions where practical.

### Privacy

-   Explain what repository data is retrieved and processed.
-   Avoid retaining source code longer than required for the scan.
-   Do not send full repositories to an LLM by default.
-   Send only relevant snippets and metadata for explanations.
-   Do not store private repository credentials in scan results.

------------------------------------------------------------------------

## 12. Hackathon MVP Scope: 4--5 Hours

The MVP must prioritise a real end-to-end workflow over feature count.

### Must-have

1.  Public GitHub repository URL input.
2.  Repository retrieval and file filtering.
3.  JavaScript/TypeScript-focused analysis.
4.  Unused-code findings using Knip or an equivalent working
    integration.
5.  Duplicate-code detection using jscpd, if integration is stable.
6.  Dependency graph and circular dependency analysis using Madge.
7.  Normalised findings with file paths and evidence.
8.  Transparent rule-based review-risk classification.
9.  AI explanation for a selected finding.
10. Dashboard and downloadable Markdown report.

### Should-have

-   Test-file mapping.
-   Coverage report ingestion.
-   Proposed patch generation.
-   Interactive graph filtering.
-   Scan history.

### Defer

-   Runtime instrumentation.
-   Automatic patch application.
-   Automatic pull-request creation.
-   Multi-language support beyond the selected implementation.
-   Full CI/CD integration.
-   Team accounts and permissions.
-   Historical repository trend analytics.

### Five-hour execution plan

  -----------------------------------------------------------------------
  Time                    Work                    Deliverable
  ----------------------- ----------------------- -----------------------
  0--30 min               Project setup, UI shell Running frontend and
                          and API structure       backend

  30--75 min              GitHub repository       Source files available
                          retrieval and filtering for analysis

  75--135 min             Integrate unused-code   Real static-analysis
                          and duplicate-code      findings
                          tools                   

  135--175 min            Dependency extraction   Graph data and cycle
                          and cycle detection     findings

  175--210 min            Finding normalisation   Evidence and
                          and risk heuristics     review-risk output

  210--245 min            AI explanation and      Explanation and
                          report generation       Markdown report

  245--280 min            Dashboard integration   End-to-end product
                          and graph display       workflow

  280--300 min            Test, fix and prepare   Reliable demonstration
                          demo                    
  -----------------------------------------------------------------------

If time is running short, prioritise repository analysis,
evidence-backed findings, dependency visualisation and the risk
explanation. Defer patch generation.

------------------------------------------------------------------------

## 13. Demo Plan

### Demo repository

Prepare a small JavaScript/TypeScript sample repository with known,
intentional examples:

-   A few genuinely unused exports.
-   Unused imports.
-   Two duplicate code blocks.
-   One circular dependency.
-   One potentially orphaned file.
-   Test files that reference selected modules.
-   One dynamically referenced component that should not be confidently
    labelled safe to remove.

Do not rely on a random external repository containing unknown issues.

### Demo sequence

1.  Enter the sample GitHub repository URL.
2.  Start the scan and show progress.
3.  Display repository statistics and findings.
4.  Open a potential unused function.
5.  Show the references and evidence used to flag it.
6.  Open the dependency graph and highlight a circular dependency.
7.  Show test files potentially related to a selected finding.
8.  Generate an AI explanation.
9.  Generate a proposed patch if implemented.
10. Download the report.

### Key demonstration moment

Show two findings with different evidence:

-   One component with no known references and no contradictory
    evidence.
-   One component with no direct static references but evidence of
    dynamic use or incomplete verification.

Demonstrate that CodeImpact does not treat both findings as equally safe
to remove.

------------------------------------------------------------------------

## 14. Success Metrics and Acceptance Criteria

### MVP success metrics

-   A supported public repository can be analysed end to end.
-   At least two real analysis categories return findings.
-   Findings include source locations where available.
-   Dependency cycles are visualised for the supported repository.
-   Risk classifications show the factors used.
-   AI explanations are grounded in backend-provided evidence.
-   A Markdown report can be downloaded.
-   The demo can be completed without manually editing the analysis
    output.

### Quality checks

-   Test against a prepared repository with known findings.
-   Check for false positives caused by dynamic imports or entry-point
    configuration.
-   Verify that tool failures are visible and not represented as zero
    findings.
-   Verify that AI cannot introduce findings absent from the analysis
    data.
-   Verify that no untrusted repository code is executed.
-   Verify that patches are never silently applied.

------------------------------------------------------------------------

## 15. Competitive Landscape and Positioning

CodeImpact operates in an established ecosystem. Relevant tools include:

-   **Knip:** Unused files, exports and dependencies for
    JavaScript/TypeScript projects.
-   **SonarQube:** Code quality, security, maintainability and
    technical-debt analysis.
-   **jscpd:** Copy/paste and duplicate-code detection.
-   **Madge:** Module dependency graphs and circular dependency
    detection.
-   **ESLint:** JavaScript/TypeScript linting and code-quality rules.
-   **Ruff:** Python linting and static checks.

CodeImpact should not claim that these tools lack dead-code detection,
dependency analysis or remediation capabilities.

### Proposed differentiation

  ---------------------------------------------------------------------
  Typical analysis workflow          CodeImpact workflow
  ---------------------------------- ----------------------------------
  Findings spread across separate    Consolidated findings
  tools                              

  Warning without enough context     Evidence and limitations shown

  Dependency graph viewed separately Dependency context attached to
                                     findings

  Developer manually judges cleanup  Transparent review-risk assessment
  priority                           

  Developer manually searches for    Suggested related tests
  tests                              

  Developer independently interprets Evidence-grounded AI explanation
  warnings                           

  Cleanup performed separately       Reviewable patch proposal
  ---------------------------------------------------------------------

### Positioning statement

CodeImpact connects code analysis, evidence, dependency context, test
recommendations and AI-assisted remediation into one
developer-controlled cleanup workflow.

The differentiation is the integrated workflow, not a claim that any
individual detection capability is unprecedented.

------------------------------------------------------------------------

## 16. Risks, Limitations and Mitigations

  -----------------------------------------------------------------------
  Risk                    Impact                  Mitigation
  ----------------------- ----------------------- -----------------------
  False-positive          Unsafe cleanup          Show evidence and
  unused-code findings    recommendation          uncertainty; account
                                                  for entry points and
                                                  dynamic usage

  Incomplete dependency   Missing impact          State supported
  graph                   relationships           language and resolution
                                                  limitations

  Dynamic imports or      Hidden runtime          Flag uncertainty;
  reflection              references              accept coverage
                                                  evidence where
                                                  available

  Large repositories      Slow or failed scans    File limits, timeouts
                                                  and asynchronous jobs

  Tool installation       MVP delay               Integrate the minimum
  issues                                          viable subset first

  LLM hallucinations      Incorrect explanations  Ground prompts in tool
                          or patches              output; validate paths
                                                  and diffs

  Prompt injection in     Unsafe model behaviour  Treat repository
  repository content                              content as untrusted
                                                  data

  Patch breaks            Regression              Require review and run
  application                                     relevant tests in
                                                  isolation

  Missing test coverage   False confidence        Display unknown rather
                                                  than assuming no impact
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 17. Future Roadmap

### Phase 2 --- Stronger Verification

-   LCOV/Istanbul coverage ingestion.
-   Runtime usage evidence through instrumentation.
-   Better dynamic-import and framework-specific analysis.
-   Improved test impact mapping.
-   Historical analysis across commits.

### Phase 3 --- Assisted Remediation

-   More reliable patch generation.
-   Isolated patch application.
-   Automated test execution in a sandbox.
-   Before/after analysis comparison.
-   Developer-approved GitHub pull requests.

### Phase 4 --- Team and CI Integration

-   GitHub App integration.
-   Pull-request checks.
-   CI/CD quality gates.
-   Team-level technical-debt trends.
-   Configurable repository policies.
-   IDE integration.

### Phase 5 --- Broader Language Support

-   Python.
-   Java.
-   Go.
-   C/C++.
-   Additional framework-aware entry-point and dependency analysis.

------------------------------------------------------------------------

## 18. Open Decisions

These decisions should be resolved during implementation:

1.  Whether the repository loader uses GitHub API file retrieval or
    shallow cloning.
2.  Which exact Knip, jscpd and Madge versions are compatible with the
    chosen runtime.
3.  Whether the MVP supports JavaScript only or JavaScript and
    TypeScript.
4.  Whether AI explanations use Gemini or an available Gemma endpoint.
5.  Whether patch generation fits within the available time.
6.  Whether scan results are stored temporarily or only returned to the
    client.

Default recommendation: public repositories, JavaScript/TypeScript, no
code execution, temporary scan storage, Gemini/Gemma explanation only
after deterministic analysis, and downloadable patches rather than
automatic commits.

------------------------------------------------------------------------

## 19. Final Product Summary

  ---------------------------------------------------------------------
  Attribute                          Definition
  ---------------------------------- ----------------------------------
  Product name                       CodeImpact

  Product category                   Codebase Intelligence / Developer
                                     Productivity

  Core problem                       Developers lack a unified,
                                     evidence-based workflow for
                                     prioritising and validating code
                                     cleanup

  Primary users                      Developers, tech leads and
                                     repository maintainers

  Primary input                      Public GitHub repository

  Core analysis                      Unused code, duplicate code and
                                     dependency relationships

  Differentiator                     Evidence-based review risk and
                                     cleanup impact

  AI role                            Explain findings and propose
                                     reviewed remediation

  Primary output                     Findings dashboard, dependency
                                     graph and Markdown report

  MVP duration                       4--5 hours

  MVP language scope                 JavaScript/TypeScript

  Safety principle                   No automatic deletion or
                                     unreviewed commits
  ---------------------------------------------------------------------

### Final product statement

**CodeImpact helps developers move from identifying potential code waste
to making informed cleanup decisions. It combines static analysis,
dependency intelligence, evidence-based risk assessment and AI-assisted
remediation so developers can understand what may be removed, why it was
flagged, what could be affected and how to validate a change---while
keeping the developer in control.**

------------------------------------------------------------------------

# 20. Hackathon Prize Integration: Open-Weight AI + Gemma 4

This section extends CodeImpact to align with the event's **Best
Open-Source AI Project** and **Best Use of Gemma 4** prize categories.

## 20.1 Gemma 4 as a core product capability

Use **Gemma 4 through the Gemini API** for the hackathon implementation.
Google's official documentation lists hosted Gemma 4 model IDs including
`gemma-4-26b-a4b-it` and `gemma-4-31b-it`. Gemma 4 is also available as
open weights for supported self-hosted deployment paths. Verify account
access, quota and the exact model ID with a live API call before the
demo.

Recommended MVP model: `gemma-4-26b-a4b-it`, subject to availability.

Gemma 4 performs product-specific tasks: - Explain static-analysis
findings using evidence supplied by CodeImpact. - Explain possible
false-positive causes and uncertainty. - Summarise dependency and test
impact. - Compare duplicate-code snippets. - Suggest refactoring
approaches. - Generate proposed diffs for developer review. - Interpret
screenshots of terminal errors, CI failures, IDE diagnostics and
architecture diagrams.

Static-analysis tools remain responsible for detecting code issues.
Gemma 4 must not invent findings or replace deterministic analysis.

## 20.2 New feature: Visual Context Inspector

**Purpose:** Let developers add visual debugging and architecture
context that may not be represented in source files or structured tool
output.

Supported image inputs: - Terminal error or stack-trace screenshots. -
CI/CD failure screenshots. - IDE diagnostic or compiler-error
screenshots. - Module or system architecture diagrams. - Code
screenshots when the original source file is difficult to locate.

### User workflow

1.  The user opens a repository analysis.
2.  The user uploads a PNG or JPEG screenshot.
3.  Gemma 4 extracts visible error messages, file names, symbols, line
    references and diagram labels.
4.  CodeImpact cross-checks extracted paths and symbols against the
    repository inventory and dependency graph.
5.  The UI separates image observations, verified repository facts and
    AI hypotheses that still require developer verification.

### Example

A developer uploads a screenshot showing:

`TypeError: Cannot read properties of undefined (reading 'userId')`

Gemma 4 extracts the error and any visible file/line references.
CodeImpact checks whether referenced files exist, identifies relevant
imports and related tests, and presents possible connections to
repository findings.

A screenshot does not prove a root cause. Interpretations must be
labelled as hypotheses unless corroborated by source or test evidence.

### Acceptance criteria

-   User can upload a PNG or JPEG screenshot.
-   Backend sends the image to Gemma 4 with a focused extraction
    instruction.
-   Model returns structured observations and an explanation.
-   UI distinguishes image observations, verified repository facts and
    hypotheses.
-   Image interpretation is not presented as proof of runtime behaviour.

## 20.3 Open-weight AI and open-source strategy

To make the open-source AI category credible: - Publish CodeImpact
source in a public GitHub repository under a team-selected licence. -
Document the analysis pipeline and Gemma 4 integration. - Include
`.env.example` with placeholders only. - Provide local setup
instructions. - Keep analysis integrations modular and documented. -
Keep Gemma 4 as the primary inference model and configure a private, provider-agnostic secondary inference route for automatic failover. The secondary route is an operational reliability mechanism, not a separately marketed product feature. - Explain that hosted Gemini API inference is being
used for the hackathon, while Gemma 4 is an open-weight model family. -
Consider optional local Gemma inference as future work if suitable
hardware is available.

Do not describe the Gemini API service itself as open source. The
open-weight element is the Gemma model; the hosted API is the inference
service.

## 20.4 Inference reliability and automatic failover

Gemma 4 remains the primary model and the model highlighted in the product, documentation, architecture diagrams and prize demonstration. Because hosted model latency and availability can vary, the backend may use a separately configured secondary inference route when the primary request exceeds its timeout, is rate-limited, is temporarily unavailable, or returns a retryable service error.

Requirements:
- Attempt Gemma 4 first for every eligible AI task.
- Trigger secondary inference only for defined transient failures; do not switch for validation errors, malformed user input or policy refusals.
- Use a bounded primary timeout, limited retry policy and an overall request deadline so failover does not make the UI appear frozen.
- Normalize both model responses to the same validated application schema.
- Keep provider selection entirely server-side. The UI must not display provider names, model-switching notices, provider logos or provider-specific metadata.
- Log operational status using neutral labels such as `primary`, `secondary`, `timeout` and `fallback_used`; never log API keys or sensitive source content.
- If both inference routes fail, return a clear deterministic message and preserve the static-analysis results.
- Do not claim that every generated explanation was produced by Gemma 4. Product and judging materials should accurately describe Gemma 4 as the primary AI model, with automatic inference failover for reliability.

The secondary route is an implementation detail. Do not expose its vendor, model name or branding in user-facing product materials.

## 20.5 Prize-focused demonstration

**Best Open-Source AI Project** - Show deterministic repository
analysis. - Select a finding. - Ask Gemma 4 to explain it using supplied
evidence. - Generate a proposed refactoring diff. - Demonstrate that the
model assists the analysis engine rather than inventing detections.

**Best Use of Gemma 4** - Upload a screenshot of a CI failure, terminal
stack trace or architecture diagram. - Show Gemma 4 extracting visible
details. - Cross-reference extracted paths or symbols with the
repository. - Display verified matches separately from AI hypotheses. -
Ask Gemma 4 to explain how the visual context may relate to repository
findings.

This is a meaningful multimodal use case, rather than an unrelated
image-upload chatbot.

## 20.5 Updated five-hour MVP priorities

  -----------------------------------------------------------------------
  Priority                Capability              Implementation
  ----------------------- ----------------------- -----------------------
  Must have               Repository analysis     GitHub + Knip or
                                                  equivalent

  Must have               Dependency and          Madge + jscpd, if
                          duplicate analysis      stable

  Must have               Evidence and risk       Deterministic backend
                          assessment              logic

  Must have               Gemma 4 finding         Hosted Gemma 4 via
                          explanation             Gemini API

  Prize differentiator    Visual Context          One screenshot upload
                          Inspector               and structured
                                                  interpretation

  Should have             AI patch proposal       Small, reviewable
                                                  unified diff

  Stretch                 Local Gemma inference   Defer unless hardware
                                                  and setup are ready
  -----------------------------------------------------------------------

If time is limited, keep Visual Context Inspector narrow: accept one
image, extract a stack trace or diagram context, and cross-check it
against the repository. Do not build a general-purpose image chat
application.

## 20.6 Updated product positioning

**CodeImpact --- Evidence-Based Codebase Intelligence, powered by Gemma
4.**

CodeImpact combines deterministic repository analysis with Gemma 4
reasoning and visual understanding. It helps developers investigate
potential technical debt, understand code relationships, interpret
visual debugging evidence and prepare developer-reviewed cleanup
proposals.
