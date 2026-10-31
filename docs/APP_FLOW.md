# CodeImpact --- Application Flow Specification

**Version:** 1.0\
**Status:** Hackathon MVP flow baseline\
**Product:** CodeImpact --- Evidence-Based Codebase Intelligence & Safe
Refactoring\
**Aligned documents:** PRD v1.2, TRD v1.2, Software Design Document v1.0

------------------------------------------------------------------------

## 1. Purpose

This document defines the end-to-end application flow for CodeImpact:
what the user sees, what they can do, how the frontend and backend
respond, how the application moves between states, and how errors or
incomplete results are handled.

It is intended to guide implementation of the frontend routes, screen
transitions, API calls, asynchronous jobs, and demo journey.

### 1.1 Core product workflow

**Connect repository → Configure analysis → Analyse → Review overview →
Explore findings → Inspect evidence and impact → Ask AI for explanation
→ Verify recommendations → Export report**

### 1.2 Secondary workflow

**Open Visual Context → Upload screenshot → Extract observations →
Verify repository matches → Review AI hypotheses → Open related
finding**

### 1.3 Non-negotiable product rules

-   A missing static reference is not proof that code is unused.
-   A finding is a review candidate, not an instruction to delete code.
-   Evidence produced by deterministic tools must be distinguishable
    from AI interpretation.
-   AI-generated explanations must be grounded in supplied analysis
    data.
-   Repository code is never executed by CodeImpact.
-   No code is deleted, modified, committed, or pushed automatically.
-   Gemma 4 is the primary AI model. Secondary inference is an internal
    reliability mechanism and must not be exposed in user-facing product
    surfaces.
-   If AI inference is unavailable, deterministic analysis and evidence
    remain usable.

------------------------------------------------------------------------

## 2. Actors and System Responsibilities

### 2.1 Actors

  -----------------------------------------------------------------------
  Actor                               Responsibility
  ----------------------------------- -----------------------------------
  Developer                           Submits a repository, reviews
                                      findings, adds visual context, and
                                      decides what to do

  Frontend application                Collects input, displays
                                      progress/results, manages
                                      navigation and user interactions

  Backend API                         Validates requests, manages
                                      analysis jobs, and serves results

  Analysis orchestrator               Runs retrieval, static analysis,
                                      graph construction, evidence
                                      collection, and risk calculation

  Static analysis tools               Detect configured code patterns and
                                      dependency information

  AI orchestration service            Explains findings, interprets
                                      supported screenshots, and creates
                                      optional patch proposals

  Report builder                      Converts completed analysis data
                                      into a portable report
  -----------------------------------------------------------------------

### 2.2 Responsibility boundary

  -----------------------------------------------------------------------
  Operation               Responsible component   Must not do
  ----------------------- ----------------------- -----------------------
  Repository URL          Backend repository      Trust frontend
  validation              service                 validation alone

  Repository retrieval    Repository service      Execute repository code

  Static analysis         Analyzer adapters       Run untrusted lifecycle
                                                  scripts

  Finding normalisation   Finding normalizer      Invent evidence not
                                                  returned by tools

  Dependency graph        Graph service           Treat an inferred edge
                                                  as a verified import

  Evidence collection     Evidence service        Convert unknown into
                                                  not-found

  Review-risk             Deterministic risk      Claim probability of
  classification          engine                  safe deletion

  AI explanation          AI orchestration        Override or fabricate
                          service                 deterministic facts

  Screenshot              Visual Context          Treat image text as
  interpretation          service + AI            trusted instructions

  Repository match        Backend inventory       Trust model-extracted
  verification            lookup                  paths without checking

  Report export           Report builder          Present hypotheses as
                                                  verified facts
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 3. Application Navigation and Route Map

### 3.1 Primary navigation

  ---------------------------------------------------------------------------------------------
  Item                    Route                                         Purpose
  ----------------------- --------------------------------------------- -----------------------
  Repository              `/`                                           Connect a repository or
                                                                        start a new analysis

  Overview                `/analysis/:analysisId`                       Review analysis summary

  Findings                `/analysis/:analysisId/findings`              Browse and filter
                                                                        findings

  Finding detail          `/analysis/:analysisId/findings/:findingId`   Inspect evidence and
                                                                        impact

  Dependency Graph        `/analysis/:analysisId/graph`                 Explore module
                                                                        relationships

  Visual Context          `/analysis/:analysisId/visual-context`        Add and inspect
                                                                        screenshots

  Reports                 `/analysis/:analysisId/reports`               Preview and export
                                                                        report
  ---------------------------------------------------------------------------------------------

### 3.2 Navigation rules

1.  The repository connection page is the application entry point.
2.  Analysis-specific navigation is available only after an analysis ID
    exists.
3.  While an analysis is running, the user can view progress and return
    to the repository page without unintentionally cancelling the job.
4.  Findings, graph, Visual Context, and reports are scoped to one
    analysis ID.
5.  When a user opens a finding and returns to the findings list,
    preserve search, filters, sort order, and page position where
    practical.
6.  A new analysis must not overwrite the previous analysis state.
7.  If a route references an unknown or expired analysis ID, show an
    actionable unavailable state and provide a route back to repository
    connection.

### 3.3 Global shell

Every analysis screen should use the same shell:

``` text
┌─────────────────────────────────────────────────────────────────┐
│ CodeImpact      owner/repository · branch       Analysis status  │
├───────────────┬─────────────────────────────────────────────────┤
│ Overview      │ Page title                         Page actions  │
│ Findings      ├─────────────────────────────────────────────────┤
│ Dependency    │                                                 │
│ Graph         │                 Main workspace                  │
│ Visual        │                                                 │
│ Context       │                                                 │
│ Reports       │                                                 │
│               │                                                 │
│ Repository    │                                                 │
└───────────────┴─────────────────────────────────────────────────┘
```

On smaller screens, the navigation collapses into a drawer or compact
menu.

------------------------------------------------------------------------

## 4. High-Level Application Flow

``` text
                       ┌──────────────────────┐
                       │   Launch CodeImpact  │
                       └──────────┬───────────┘
                                  │
                                  v
                       ┌──────────────────────┐
                       │ Repository Connect   │
                       │ URL + optional branch│
                       └──────────┬───────────┘
                                  │ Submit
                                  v
                       ┌──────────────────────┐
                       │ Validate Repository  │
                       └──────────┬───────────┘
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                  Invalid                    Valid
                     │                         │
                     v                         v
             ┌──────────────┐       ┌──────────────────────┐
             │ Show error   │       │ Create analysis job  │
             │ Keep input   │       └──────────┬───────────┘
             └──────────────┘                  │
                                               v
                                    ┌──────────────────────┐
                                    │ Analysis Progress    │
                                    └──────────┬───────────┘
                                               │
                                               v
                                    ┌──────────────────────┐
                                    │ Retrieve source      │
                                    │ Detect project       │
                                    │ Run analyzers        │
                                    │ Build dependency map │
                                    │ Collect evidence     │
                                    │ Calculate review risk│
                                    └──────────┬───────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │                           │
                              Failed                 Complete / Partial
                                 │                           │
                                 v                           v
                        ┌────────────────┐       ┌────────────────────┐
                        │ Failure state  │       │ Analysis Overview  │
                        └────────────────┘       └─────────┬──────────┘
                                                           │
                   ┌───────────────────────────────────────┼───────────────────────┐
                   │                  │                    │                       │
                   v                  v                    v                       v
             ┌──────────┐      ┌─────────────┐      ┌────────────┐          ┌───────────┐
             │ Findings │      │ Graph       │      │ Visual     │          │ Reports   │
             │ Explorer │      │ Explorer    │      │ Context    │          │ Export    │
             └────┬─────┘      └─────────────┘      └─────┬──────┘          └───────────┘
                  │                                       │
                  v                                       v
             ┌─────────────┐                       ┌────────────────┐
             │ Finding     │                       │ Extract image  │
             │ Detail      │                       │ observations   │
             └────┬────────┘                       └───────┬────────┘
                  │                                        │
                  v                                        v
             ┌─────────────┐                       ┌────────────────┐
             │ AI Explain  │                       │ Verify paths   │
             │ (optional)  │                       │ and symbols    │
             └────┬────────┘                       └───────┬────────┘
                  │                                        │
                  v                                        v
             ┌─────────────┐                       ┌────────────────┐
             │ Review next │                       │ Open related   │
             │ steps       │                       │ finding        │
             └─────────────┘                       └────────────────┘
```

------------------------------------------------------------------------

## 5. Flow 1 --- Launch and Repository Connection

### 5.1 Entry state

When the user opens CodeImpact, show the repository connection screen.
Do not require account creation or AI configuration for the MVP.

### 5.2 Screen elements

-   CodeImpact logo/name
-   Short product statement
-   GitHub repository URL field
-   Optional branch field
-   Primary **Analyse repository** button
-   Supported repository note
-   Public repository/security note
-   Optional **Try sample repository** action

### 5.3 User flow

1.  User pastes a repository URL.
2.  User optionally enters a branch.
3.  User selects **Analyse repository**.
4.  Frontend performs basic input checks.
5.  Frontend sends the request to backend.
6.  Backend validates the URL and repository accessibility.
7.  Backend retrieves repository metadata and resolves the
    branch/commit.
8.  Backend creates an analysis job and returns an analysis ID.
9.  Frontend navigates to the progress screen.

### 5.4 Input validation

  -----------------------------------------------------------------------
  Condition                           Expected behaviour
  ----------------------------------- -----------------------------------
  Empty URL                           Show "Enter a GitHub repository
                                      URL."

  Invalid URL format                  Show inline validation error

  Unsupported host                    Reject request

  Private or inaccessible repository  Explain that the MVP supports
                                      accessible public repositories

  Invalid branch                      Show branch error; allow correction

  Repository exceeds limits           Explain the applicable size/file
                                      limit

  URL contains embedded credentials   Reject and do not log the value

  Duplicate click                     Prevent duplicate job submission
  -----------------------------------------------------------------------

### 5.5 API interaction

**Request:** `POST /api/repositories/analyse`

Example request:

``` json
{
  "repository_url": "https://github.com/owner/repository",
  "branch": "main"
}
```

Example response:

``` json
{
  "analysis_id": "an_123456",
  "status": "queued",
  "repository": "owner/repository",
  "branch": "main",
  "commit_sha": "optional-commit-sha"
}
```

Expected HTTP status: `202 Accepted`.

### 5.6 Transition

`Repository Connection → Analysis Progress`

The analysis ID becomes the key for all subsequent requests.

------------------------------------------------------------------------

## 6. Flow 2 --- Analysis Progress and Orchestration

### 6.1 Purpose

Analysis is asynchronous. The frontend must not hold a single request
open until all repository tools complete.

### 6.2 Pipeline stages

  ------------------------------------------------------------------------
                  Order Stage            Backend          User-facing
                                         operation        label
  --------------------- ---------------- ---------------- ----------------
                      1 Validation       Confirm          Validating
                                         repository,      repository
                                         branch, limits   

                      2 Retrieval        Retrieve         Retrieving
                                         metadata and     source files
                                         source files     

                      3 Detection        Identify         Detecting
                                         language,        project
                                         package manager, structure
                                         entry points     

                      4 Static analysis  Run configured   Running static
                                         analysers        analysis

                      5 Dependency graph Build            Building
                                         file/module      dependency graph
                                         graph and detect 
                                         cycles           

                      6 Evidence         Find references, Collecting
                        collection       dependants,      evidence
                                         tests, dynamic   
                                         indicators       

                      7 Risk calculation Apply            Assessing review
                                         transparent      priority
                                         deterministic    
                                         rules            

                      8 Result           Persist          Preparing
                        preparation      findings,        results
                                         metrics, and     
                                         report inputs    
  ------------------------------------------------------------------------

### 6.3 Frontend behaviour

-   Poll `GET /api/analyses/{analysis_id}` at a controlled interval.
-   Display current stage and completed stages.
-   Show elapsed time if available.
-   Do not fabricate a percentage when the backend only reports stage
    names.
-   Keep the user on the progress screen until the analysis reaches a
    terminal state.
-   If the user navigates away, the backend job continues unless
    explicitly cancelled by a supported cancellation feature.

### 6.4 Terminal states

  -----------------------------------------------------------------------
  Status                  Meaning                 UI behaviour
  ----------------------- ----------------------- -----------------------
  `completed`             All required stages     Navigate to Overview
                          completed               

  `partial`               Some non-critical       Navigate to Overview
                          stages did not complete with partial-result
                                                  warning

  `failed`                A required stage failed Show failure summary
                                                  and retry/new-analysis
                                                  options

  `running`               Job still executing     Continue progress
                                                  updates

  `queued`                Job waiting to start    Show queued state
  -----------------------------------------------------------------------

### 6.5 Partial analysis behaviour

If one optional analyser fails: - Preserve findings from successful
tools. - Mark failed tool coverage as unavailable. - Show which category
may be incomplete. - Do not infer that no findings exist for the failed
category.

### 6.6 Failure behaviour

If a required stage fails: - Show a concise message and request ID. - Do
not display raw subprocess output or stack traces. - Offer retry only
when the backend supports safe retry. - Keep repository input and
metadata available to avoid unnecessary re-entry.

### 6.7 Transition

`Analysis Progress → Overview` for `completed` or `partial`;
`Analysis Progress → Failure State` for `failed`.

------------------------------------------------------------------------

## 7. Flow 3 --- Overview Dashboard

### 7.1 Entry

The overview loads after a completed or partial analysis.

### 7.2 Data requested

`GET /api/analyses/{analysis_id}`

The response should include: - Repository metadata - Branch and commit -
Analysis status - Timestamp - Summary metrics - Tool coverage -
Error/partial summary - Finding counts by category and review risk

### 7.3 Screen sequence

1.  Show repository identity and analysis status.
2.  Render metric cards.
3.  Render finding distribution.
4.  Render review-risk distribution.
5.  Render dependency-cycle summary.
6.  Show recommended next steps based on deterministic results.
7.  Show tool coverage and analysis limitations.
8.  Provide navigation to detailed modules.

### 7.4 Overview interactions

  -----------------------------------------------------------------------
  User action                         System response
  ----------------------------------- -----------------------------------
  Select total findings               Open Findings with no category
                                      filter

  Select a category count             Open Findings filtered to that
                                      category

  Select higher review-risk count     Open Findings filtered to higher

  Select cycle count                  Open Dependency Graph focused on
                                      cycle information

  Select a recommendation             Open relevant finding or graph
                                      context

  Select Visual Context               Open screenshot workflow

  Select Reports                      Open report preview/export
  -----------------------------------------------------------------------

### 7.5 Zero-findings state

Display: "No findings were returned by the configured checks."

Also show: - Which analysers ran - Which categories were checked - Known
limitations

Do not display "Your codebase is clean" or "No technical debt exists."

------------------------------------------------------------------------

## 8. Flow 4 --- Findings Explorer

### 8.1 Entry

User selects Findings from navigation or a metric card.

### 8.2 Initial load

Frontend calls:

`GET /api/analyses/{analysis_id}/findings`

Optional query parameters: - `category` - `review_risk` -
`evidence_class` - `source_tool` - `file_path` - `search` - `sort` -
`page` - `page_size`

### 8.3 User actions

  Action                  Expected behaviour
  ----------------------- ------------------------------------------------------
  Search                  Match finding title, file path, symbol, and category
  Filter by category      Show only selected category
  Filter by review risk   Show selected review-priority group
  Filter by evidence      Show selected evidence classification
  Sort                    Reorder results consistently
  Open finding            Navigate to finding detail
  Clear filters           Restore unfiltered list
  Return from detail      Restore previous list state

### 8.4 Findings list states

-   Loading: skeleton rows or compact loading indicator.
-   Results: table or responsive cards.
-   Empty: no findings exist for the selected filters.
-   Error: show retry action.
-   Partial: banner indicates incomplete analyser coverage.

### 8.5 Transition

`Findings Explorer → Finding Detail`

------------------------------------------------------------------------

## 9. Flow 5 --- Finding Detail and Evidence Review

### 9.1 Entry

User selects a finding.

### 9.2 Data requested

`GET /api/analyses/{analysis_id}/findings/{finding_id}`

The detail response should include: - Finding identity and category -
File path and line range - Source tool - Raw analyser observation or
reference - Evidence list - Review-risk label and factors - Dependency
context - Test candidates - Analysis limitations - Existing AI
explanation, if cached

### 9.3 Screen reading order

1.  Finding title and classification
2.  What was detected
3.  Evidence
4.  Dependency and impact context
5.  Related test candidates
6.  Uncertainty and limitations
7.  AI explanation
8.  Review actions

### 9.4 Evidence interpretation

Each evidence row must expose: - Evidence type - Status - Value or
result - Collection method/source - Limitation or note

Status definitions:

  Status          Meaning
  --------------- ------------------------------------------------
  `found`         Evidence was found by the specified method
  `not_found`     The specified method did not find the evidence
  `unknown`       The system cannot determine the value
  `not_checked`   The corresponding check was not run
  `conflicting`   Available evidence sources disagree

### 9.5 Review-risk explanation

The risk panel must show the factors that influenced the category.
Example factors: - Entry-point relationship - Number of dependants -
Dynamic import indicators - Framework/configuration indicators - Related
tests - Evidence completeness

Risk labels: - Lower - Medium - Higher - Unknown

These labels represent review priority, not deletion-safety probability.

### 9.6 User actions

  Action                    Result
  ------------------------- ----------------------------------------------
  Explain with AI           Start AI explanation flow
  View in graph             Navigate to graph with selected file focused
  View test candidates      Expand related test section
  Copy summary              Copy a concise evidence-based summary
  Generate patch proposal   Start optional read-only diff generation
  Back to findings          Restore previous filters and position

### 9.7 Human-control rule

No action on this screen may directly delete a file, modify source,
commit, push, or create a pull request.

------------------------------------------------------------------------

## 10. Flow 6 --- AI Explanation and Inference Reliability

### 10.1 Entry

User selects **Explain with AI** from a finding detail screen.

### 10.2 Request context

Backend constructs a bounded context package containing: - Finding
metadata - Evidence items - Relevant graph neighbours - Test
candidates - Tool coverage and limitations - Small relevant source
excerpts, if available and safe - Optional verified Visual Context
observations

The entire repository must not be sent by default.

### 10.3 Inference sequence

``` text
User selects Explain
        |
        v
Validate finding and build context
        |
        v
Call primary Gemma 4 route
        |
        v
Validate response schema
        |
        +---- Valid response --------------------+
        |                                         |
        |                                         v
        |                                Render explanation
        |
        +---- Timeout / transient failure
                         |
                         v
              Invoke secondary inference
                         |
              +----------+-----------+
              |                      |
           Valid                  Failure
              |                      |
              v                      v
       Render explanation     Build deterministic
                              evidence-based response
                                      |
                                      v
                              Render availability
                              notice if necessary
```

### 10.4 Frontend response states

**Loading** - Show "Preparing explanation...". - Keep the finding
evidence visible. - Prevent accidental duplicate requests.

**Success** Render structured sections: - Summary - Why it matters -
Possible false positives - Verification steps - Suggested action -
Limitations

**Fallback success** - Render the same schema and layout as the primary
route. - Do not expose model/provider identity or switching details.

**Deterministic response** - Clearly label it as an evidence-based
summary rather than an AI-generated explanation. - Keep the user
informed that AI explanation is temporarily unavailable.

**Failure** - Show a retry action. - Do not hide the underlying
static-analysis evidence.

### 10.5 AI trust rules

-   AI must not invent paths, symbols, test files, tool results, or
    graph edges.
-   AI must not claim that a candidate is safe to delete.
-   AI must identify uncertainty and possible false positives.
-   AI output must be schema-validated.
-   Model-generated suggestions are advisory only.
-   User-facing interface must not display provider routing details.

------------------------------------------------------------------------

## 11. Flow 7 --- Dependency Graph Exploration

### 11.1 Entry

User selects Dependency Graph from navigation or a finding action.

### 11.2 Data request

`GET /api/analyses/{analysis_id}/graph`

Optional query parameters: - `focus_file` - `directory` - `cycle_only` -
`has_findings` - `max_nodes`

### 11.3 Initial graph load

1.  Load graph metadata and bounded node/edge set.
2.  Render file nodes and directed dependency edges.
3.  Render cycle summary.
4.  Display graph legend and controls.
5.  If graph rendering fails, show textual dependency/cycle list.

### 11.4 Interactions

  Interaction           Result
  --------------------- ---------------------------------------------------
  Select node           Show file metadata, imports, dependants, findings
  Select edge           Show source and target relationship
  Search path           Focus matching node
  Show cycles           Highlight cycle members and list cycle paths
  Filter by directory   Show selected directory/subgraph
  Filter findings       Highlight nodes associated with findings
  Fit graph             Fit visible nodes to viewport
  Open finding          Navigate to relevant finding detail

### 11.5 Graph limitations

-   A graph edge represents an observed dependency relationship from
    configured analysis.
-   The graph may not include runtime-generated or dynamically resolved
    dependencies.
-   Large graphs may be truncated or filtered.
-   The textual representation must remain available.

------------------------------------------------------------------------

## 12. Flow 8 --- Visual Context Inspector

### 12.1 Entry

User selects Visual Context from navigation.

### 12.2 Upload screen

Display: - Drag-and-drop/file picker - Accepted formats: PNG and JPEG -
Maximum file size and image dimension limits - Context type selector: -
Terminal error - CI failure - IDE diagnostic - Architecture diagram -
Code screenshot - Optional related finding selector - Warning not to
upload secrets or sensitive production data - Explicit **Analyse image**
action

### 12.3 Upload validation

Frontend checks: - A file is selected. - Extension and reported MIME
type are supported. - File size is within the configured limit.

Backend independently checks: - Actual file signature. - Actual MIME
type. - Image dimensions. - File size. - Analysis ID validity. - Context
type validity.

Reject SVG, HTML, archives, and remote image URLs.

### 12.4 API request

`POST /api/analyses/{analysis_id}/visual-context`

Use multipart form data: - `image` - `context_type` - Optional
`finding_id`

### 12.5 Processing flow

``` text
Select image
    |
    v
Validate file
    |
    v
Upload to backend
    |
    v
Validate signature, size, dimensions
    |
    v
Build bounded repository context
    |
    v
Ask primary multimodal model to extract observations
    |
    v
Validate structured output
    |
    v
Cross-check paths and symbols against repository
    |
    v
Return observations + verified matches + hypotheses
    |
    v
Render Visual Context results
```

### 12.6 Result sections

**A. Observed in image** - Extracted error text - File paths - Symbols -
Line numbers - Diagram labels/relationships

These are model-extracted observations and may contain mistakes.

**B. Matched in repository** - Exact path matches - Approximate path
matches - Symbol matches - No match

Each match must include the backend verification source.

**C. AI hypotheses** - Possible interpretation - Potentially related
module or finding - Suggested verification step

Every hypothesis must be visibly labelled as unverified.

### 12.7 Follow-up actions

-   Open matched file/finding.
-   Link visual context to a finding.
-   Copy a concise context summary.
-   Remove the visual context if the application supports deletion.

### 12.8 Failure states

  -----------------------------------------------------------------------
  Failure                             User message/action
  ----------------------------------- -----------------------------------
  Unsupported image                   Ask user to upload PNG or JPEG

  Oversized image                     Show configured upload limit

  Invalid image signature             Reject the file

  Image interpretation unavailable    Keep upload status clear and allow
                                      retry

  No repository matches               Explain that no exact match was
                                      verified

  Partial extraction                  Show extracted items and mark
                                      missing sections

  Inference unavailable               Preserve deterministic repository
                                      evidence and offer retry
  -----------------------------------------------------------------------

### 12.9 Security rules

-   Treat image text as untrusted input.
-   Do not follow instructions embedded in screenshots.
-   Never let image content trigger shell commands or repository
    modifications.
-   Delete temporary image data according to retention policy.
-   Do not log raw image contents.

------------------------------------------------------------------------

## 13. Flow 9 --- Patch Proposal (Optional/Stretch)

### 13.1 Entry

User selects **Generate patch proposal** from a finding detail page.

### 13.2 Processing

1.  Backend validates finding and repository context.
2.  Backend supplies only relevant code excerpts and evidence.
3.  AI generates a unified diff proposal.
4.  Backend validates diff structure and referenced paths.
5.  Frontend renders the diff in read-only mode.
6.  User reviews the proposed changes.

### 13.3 User actions

-   View diff
-   Copy diff
-   Reject proposal
-   Return to finding

### 13.4 Explicit exclusions

The MVP does not: - Apply patch to repository automatically - Write
changes into the cloned source tree - Commit or push changes - Create a
pull request - Claim that the patch is correct without tests

The diff is a proposal requiring human review and independent
validation.

------------------------------------------------------------------------

## 14. Flow 10 --- Report Preview and Export

### 14.1 Entry

User selects Reports.

### 14.2 Data source

The report is built from persisted analysis results. Export must not
rerun analysers or unexpectedly regenerate AI explanations.

### 14.3 Report composition

1.  Repository and branch details
2.  Analysis timestamp and status
3.  Tool coverage
4.  Executive summary
5.  Findings by category
6.  Review-risk distribution
7.  Dependency cycles
8.  Duplicate-code groups
9.  Test-impact candidates
10. AI explanations, clearly labelled
11. Visual Context observations, if included
12. Analysis limitations
13. Developer verification checklist

### 14.4 User actions

-   Preview report
-   Download Markdown
-   Return to findings
-   Return to overview

### 14.5 Export rules

-   Markdown is the MVP format.
-   Preserve file paths, line references, evidence labels, and
    limitations.
-   Do not call hypotheses verified facts.
-   Include the analysis commit/branch to identify the code snapshot.

------------------------------------------------------------------------

## 15. Flow 11 --- Starting Another Analysis

### 15.1 Entry

User selects **New analysis** from the top bar or Repository navigation.

### 15.2 Behaviour

1.  Navigate to repository connection page.
2.  Preserve the previous analysis as a separate analysis record if
    storage supports it.
3.  Accept a new repository/branch.
4.  Create a new analysis ID.
5.  Do not mix findings, graph data, or visual contexts between
    analyses.

### 15.3 Analysis isolation

Every request for findings, graph, visual context, explanations, and
reports must be scoped to the correct analysis ID. The backend must
verify that each finding ID belongs to the requested analysis.

------------------------------------------------------------------------

## 16. Application State Model

### 16.1 Analysis job state

``` text
CREATED
   |
   v
QUEUED
   |
   v
RUNNING
   |-------------------------|
   |                         |
   v                         v
COMPLETED                  PARTIAL
   |                         |
   +------------+------------+
                |
                v
          REVIEW AVAILABLE

RUNNING --required stage failure--> FAILED
```

### 16.2 Frontend screen state

  -----------------------------------------------------------------------
  Screen                              States
  ----------------------------------- -----------------------------------
  Repository                          Idle, validating, invalid,
                                      submitting, rejected

  Progress                            Queued, running, partial,
                                      completed, failed

  Overview                            Loading, ready, empty, partial,
                                      error

  Findings                            Loading, results, no results, no
                                      filter matches, error

  Finding detail                      Loading, ready, missing finding,
                                      error

  Graph                               Loading, ready, empty, truncated,
                                      unavailable

  Visual Context                      Empty, selected, uploading,
                                      processing, results, partial, error

  AI explanation                      Not requested, loading, success,
                                      deterministic-only, unavailable

  Reports                             Loading, preview, exporting,
                                      exported, error

  Patch proposal                      Not requested, generating, ready,
                                      invalid, unavailable
  -----------------------------------------------------------------------

### 16.3 State ownership

-   Server-owned state: analysis status, findings, evidence, graph, AI
    explanations, visual context, report inputs.
-   Client-owned state: current route, filters, sort order, open panels,
    unsaved form input.
-   Do not use frontend state as the source of truth for analysis
    completion or verified repository matches.

------------------------------------------------------------------------

## 17. API Call Sequence Summary

  -----------------------------------------------------------------------------------------------
  User flow               API call                                        When
  ----------------------- ----------------------------------------------- -----------------------
  Start analysis          `POST /api/repositories/analyse`                User submits repository

  Poll analysis           `GET /api/analyses/{id}`                        While queued/running;
                                                                          refresh overview

  Load findings           `GET /api/analyses/{id}/findings`               Findings screen opens
                                                                          or filters change

  Load finding            `GET /api/analyses/{id}/findings/{findingId}`   Finding detail opens

  Load graph              `GET /api/analyses/{id}/graph`                  Graph screen opens or
                                                                          filters change

  Explain finding         `POST /api/analyses/{id}/explain`               User requests AI
                                                                          explanation

  Generate patch          `POST /api/analyses/{id}/patch`                 User requests proposal

  Analyse screenshot      `POST /api/analyses/{id}/visual-context`        User uploads image

  Export report           `GET /api/analyses/{id}/report`                 User downloads report
  -----------------------------------------------------------------------------------------------

### API interaction requirements

-   Use request IDs for traceability.
-   Return stable error codes.
-   Validate all input on the backend.
-   Use asynchronous jobs for long-running operations.
-   Apply pagination/limits to findings and graph responses.
-   Avoid returning raw tool output or stack traces to the frontend.
-   Use bounded timeouts and retries.
-   Ensure every resource is scoped to the correct analysis.

------------------------------------------------------------------------

## 18. Error Handling and Recovery Matrix

  ------------------------------------------------------------------------------------
  Scenario          Detection point   User-facing       Recovery
                                      response          
  ----------------- ----------------- ----------------- ------------------------------
  Invalid           Backend           Explain accepted  Edit URL
  repository URL    validation        URL format        

  Repository        Retrieval         Explain public    Check URL/access
  inaccessible                        repository        
                                      requirement       

  Branch missing    Metadata          Explain branch    Choose branch
                    retrieval         not found         

  Repository too    Retrieval limits  Explain supported Try smaller repository
  large                               limits            

  One analyser      Analyzer stage    Partial analysis  Review available results
  fails                               warning           

  Required stage    Orchestrator      Analysis failed   Retry or start new analysis
  fails                               with request ID   

  Graph too large   Graph service     Show bounded      Filter/subgraph/text list
                                      graph notice      

  AI primary route  AI orchestrator   No provider       Automatic failover
  times out                           details; continue 
                                      silently if       
                                      fallback succeeds 

  All inference     AI orchestrator   AI explanation    Retry later; inspect evidence
  routes fail                         temporarily       
                                      unavailable       

  Invalid AI JSON   Schema validator  Treat as          Retry/failover/deterministic
                                      inference failure response

  Invalid           Upload validation Explain accepted  Select another image
  screenshot                          file requirements 

  Screenshot has no Repository        Show observations Search manually/open findings
  matches           cross-check       with no verified  
                                      match             

  Report generation Report service    Explain export    Retry export
  fails                               failure           

  Analysis ID       API               Analysis no       Start a new analysis
  expired                             longer available  
  ------------------------------------------------------------------------------------

Error messages must be concise and actionable. Technical details belong
in restricted logs, not the user interface.

------------------------------------------------------------------------

## 19. Data and Evidence Provenance Flow

CodeImpact must preserve provenance as data moves through the system.

``` text
Repository source
      |
      v
Static analyser output -----------+
      |                            |
      v                            v
Finding normalizer           Dependency graph
      |                            |
      +-------------+--------------+
                    |
                    v
             Evidence collector
                    |
                    v
             Review-risk engine
                    |
                    v
           Persisted analysis data
                    |
          +---------+----------+
          |                    |
          v                    v
    Frontend findings      AI context package
          |                    |
          |                    v
          |             AI explanation
          |                    |
          +---------+----------+
                    |
                    v
             Report builder
```

### Provenance rules

-   Tool observations retain the source tool and original reference.
-   Derived evidence identifies the method used to calculate it.
-   Risk classification retains its contributing factors.
-   AI explanations are stored separately from deterministic findings.
-   Screenshot observations retain their image-extraction origin.
-   Repository matches are created only after backend verification.
-   Hypotheses remain explicitly unverified.

------------------------------------------------------------------------

## 20. User Journey and Interaction Details

### 20.1 First-time developer

1.  Opens CodeImpact.
2.  Understands the product purpose from the landing screen.
3.  Pastes a public GitHub URL.
4.  Starts analysis without configuring model credentials.
5.  Sees progress stages.
6.  Reviews the overview.
7.  Opens a finding and understands evidence/uncertainty.
8.  Requests an AI explanation.
9.  Exports a report.

### 20.2 Developer investigating a suspicious file

1.  Opens Findings.
2.  Searches by file path or symbol.
3.  Opens the candidate finding.
4.  Reviews direct references and graph relationships.
5.  Checks dynamic usage indicators and test candidates.
6.  Requests explanation.
7.  Follows verification steps outside CodeImpact.
8.  Records their own decision in their development workflow.

### 20.3 Developer investigating a CI failure

1.  Opens Visual Context.
2.  Uploads a CI screenshot.
3.  Selects CI failure as context type.
4.  Reviews extracted error text and file paths.
5.  Checks which paths and symbols matched the repository.
6.  Reviews hypotheses separately.
7.  Opens a related finding or graph node.
8.  Uses the evidence to continue debugging.

------------------------------------------------------------------------

## 21. Suggested Frontend Implementation Sequence

### Phase A --- App foundation

-   Create route structure and app shell.
-   Implement shared navigation and page header.
-   Add API client and typed response models.
-   Add global loading/error/toast handling.

### Phase B --- Repository and analysis

-   Implement repository form and validation.
-   Connect analysis creation endpoint.
-   Implement progress screen and status polling.
-   Handle completed, partial, and failed states.

### Phase C --- Results

-   Implement overview metrics.
-   Implement findings list, search, and filters.
-   Implement finding detail and evidence list.
-   Preserve list state during navigation.

### Phase D --- Intelligence views

-   Implement dependency graph and textual fallback.
-   Implement AI explanation panel.
-   Add stable loading, failure, and deterministic-only states.

### Phase E --- Multimodal and reporting

-   Implement image upload and validation.
-   Render observations, verified matches, and hypotheses separately.
-   Implement Markdown report preview/download.
-   Add optional patch proposal viewer if time allows.

------------------------------------------------------------------------

## 22. Hackathon Demo Flow

The demo should tell one coherent story rather than showing disconnected
features.

### Recommended 4--6 minute sequence

  -----------------------------------------------------------------------
  Time                    Action                  Message to communicate
  ----------------------- ----------------------- -----------------------
  0:00--0:30              Introduce repository    CodeImpact starts from
                          connection              a real codebase

  0:30--1:00              Submit repository and   Analysis is a
                          show progress           structured pipeline

  1:00--1:45              Show overview metrics   Results are summarised
                                                  and traceable

  1:45--2:45              Open a finding          Evidence and
                                                  uncertainty are visible

  2:45--3:30              Request AI explanation  AI explains evidence
                                                  rather than replacing
                                                  analysis

  3:30--4:15              Show dependency graph   Findings are connected
                                                  to repository structure

  4:15--5:00              Upload CI screenshot    Multimodal observations
                                                  are checked against the
                                                  repository

  5:00--5:30              Export report           The workflow produces a
                                                  portable developer
                                                  artifact
  -----------------------------------------------------------------------

### Demo reliability checklist

-   Use a tested public repository.
-   Keep a known fixture or precomputed result as backup.
-   Verify the primary AI route before presenting.
-   Verify automatic failover behaviour separately.
-   Keep a sample PNG/JPEG screenshot ready.
-   Confirm graph rendering on the demo repository.
-   Test report download.
-   Avoid relying on live external services for every step of the
    presentation.

------------------------------------------------------------------------

## 23. Acceptance Checklist

### Repository and analysis

-   [ ] Repository URL is validated on frontend and backend.
-   [ ] Only supported public GitHub repositories are accepted.
-   [ ] Analysis starts asynchronously and returns an analysis ID.
-   [ ] Progress stages accurately reflect backend status.
-   [ ] Partial and failed states are handled.

### Findings and evidence

-   [ ] Findings are filterable and searchable.
-   [ ] Finding details show evidence source and status.
-   [ ] Unknown, not-checked, and not-found are distinct.
-   [ ] Review risk includes explanatory factors.
-   [ ] Findings are never presented as automatic deletion instructions.

### AI

-   [ ] Gemma 4 is the primary model.
-   [ ] AI responses follow one validated schema.
-   [ ] Timeout and automatic secondary inference are handled
    internally.
-   [ ] The frontend does not expose provider identity or routing.
-   [ ] Deterministic evidence remains available when AI is unavailable.
-   [ ] AI output cannot execute commands or modify repository files.

### Graph

-   [ ] Directed dependencies can be explored.
-   [ ] Cycles can be identified.
-   [ ] Node selection links to findings.
-   [ ] Textual fallback is available.

### Visual Context

-   [ ] PNG/JPEG validation works.
-   [ ] Observations, repository matches, and hypotheses are distinct.
-   [ ] Paths/symbols are backend-verified before being labelled as
    matches.
-   [ ] Screenshot content is treated as untrusted.

### Reports and safety

-   [ ] Markdown report includes analysis metadata and limitations.
-   [ ] Export uses persisted results.
-   [ ] Repository code is never executed.
-   [ ] No automatic code changes, commits, or pushes occur.
-   [ ] Temporary repository and image data are cleaned according to
    policy.

------------------------------------------------------------------------

## 24. Final Application Flow Summary

CodeImpact is organised around a single analysis workspace. The
developer begins by connecting a public repository. The backend
retrieves and analyses the codebase asynchronously, then presents an
overview of findings, dependency relationships, evidence, and review
priorities. The developer can inspect individual findings, request an AI
explanation, explore graph context, add a screenshot through Visual
Context, and export a report.

The most important distinction throughout the flow is between:

1.  **Observed:** What configured tools or image extraction returned.
2.  **Verified:** What the backend confirmed against repository data.
3.  **Interpreted:** What AI suggests based on the supplied evidence.
4.  **Decided:** What the developer chooses to review or change.

CodeImpact supports investigation and decision-making. It does not
replace developer judgement or make code changes automatically.
