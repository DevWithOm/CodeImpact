# CodeImpact --- Software Design Document (SDD)

**Version:** 1.0\
**Status:** Hackathon MVP design baseline\
**Product:** CodeImpact --- Evidence-Based Codebase Intelligence & Safe
Refactoring\
**Related specifications:** CodeImpact PRD v1.2 and TRD v1.2\
**Primary AI capability:** Gemma 4\
**Document purpose:** Define the product experience, system structure,
component responsibilities, interaction patterns, data contracts, visual
language, and safety rules needed to implement a coherent CodeImpact
MVP.

------------------------------------------------------------------------

## 1. Document Overview

### 1.1 Purpose

This document translates the product and technical requirements into an
implementable design. It describes how a developer moves through
CodeImpact, how the interface presents evidence, how backend services
collaborate, and how AI-generated explanations are constrained.

The design is intentionally focused on a narrow, demonstrable workflow:

**Connect repository → Analyse → Inspect findings → Verify evidence →
Understand impact → Review recommendations → Export report**

A second workflow adds multimodal context:

**Add screenshot → Extract observations → Match observations to
repository evidence → Review hypotheses**

### 1.2 Design principles

1.  **Evidence before interpretation:** Every finding should show the
    observable evidence that produced it.
2.  **Impact before action:** A candidate is not labelled safe to delete
    merely because a static analyser did not find a reference.
3.  **Human-controlled changes:** CodeImpact never deletes, edits,
    commits, or pushes code automatically.
4.  **Deterministic core, AI-assisted explanation:** Static analysis and
    graph calculations produce the facts; the AI explains those facts
    and proposes reviewable next steps.
5.  **Visible uncertainty:** Dynamic imports, reflection, framework
    conventions, generated code, runtime configuration, and incomplete
    test coverage must remain visible limitations.
6.  **One consistent contract:** Primary and secondary inference routes
    return the same application schema. Provider selection is not
    exposed in the product UI.
7.  **Progressive disclosure:** Show a concise repository summary first;
    expose technical evidence and caveats when the user opens a finding.
8.  **Fast demo, credible product:** The MVP should feel like a focused
    developer tool, not a generic AI chat interface.

### 1.3 Intended audience

-   Frontend and backend implementers
-   Product/design contributors
-   Hackathon judges and demo reviewers
-   Future maintainers extending the MVP

### 1.4 Scope boundary

The design targets public GitHub repositories and an initial
JavaScript/TypeScript analysis path. It does not promise complete
semantic dead-code proof, execution tracing, universal language support,
or automated safe deletion.

------------------------------------------------------------------------

## 2. Product Experience at a Glance

### 2.1 Primary user journey

  -----------------------------------------------------------------------
  Step              User action       System response   User-visible
                                                        result
  ----------------- ----------------- ----------------- -----------------
  1                 Enters a public   Validates URL and Repository
                    GitHub repository retrieves         identity and
                    URL and branch    repository        selected branch
                                      metadata/files    

  2                 Starts analysis   Creates an        Progress state
                                      analysis job and  and completed
                                      runs configured   stages
                                      tools             

  3                 Opens overview    Aggregates        Repository health
                                      findings, graph   snapshot
                                      metrics, and risk 
                                      distribution      

  4                 Opens a finding   Loads evidence,   Explainable
                                      references, graph finding detail
                                      neighbours, and   
                                      test candidates   

  5                 Requests          Sends bounded     Structured
                    explanation       finding context   explanation and
                                      to AI             suggested next
                                      orchestration     steps

  6                 Reviews           Shows optional    Explicit
                    recommendation    patch proposal as review-only
                                      a diff            action

  7                 Exports report    Builds Markdown   Downloadable
                                      report from       analysis report
                                      persisted         
                                      analysis data     
  -----------------------------------------------------------------------

### 2.2 Visual Context Inspector journey

1.  User opens **Visual Context** within an existing analysis.
2.  User uploads one PNG or JPEG image, optionally selecting its context
    type.
3.  Backend validates the image, forwards it to the configured AI
    orchestration service, and receives structured observations.
4.  Backend cross-checks extracted paths and symbols against the
    repository inventory and analysis graph.
5.  UI displays three distinct groups:
    -   **Observed in image** --- extracted text, path, symbol, line, or
        diagram label.
    -   **Matched in repository** --- exact or approximate matches
        verified by backend lookup.
    -   **AI hypotheses** --- possible interpretations that require
        developer verification.
6.  User can open a matched finding or copy a concise context summary
    into a finding explanation request.

A screenshot is contextual evidence, not proof of runtime behaviour or
root cause.

------------------------------------------------------------------------

## 3. Information Architecture

### 3.1 Application navigation

Use a compact, persistent left navigation on desktop and a collapsible
navigation drawer on smaller screens.

  -----------------------------------------------------------------------
  Navigation item         Purpose                 Availability
  ----------------------- ----------------------- -----------------------
  Overview                Current analysis        After an analysis
                          summary and key metrics exists

  Findings                Search, filter, sort,   After an analysis
                          and inspect findings    exists

  Dependency Graph        Explore file/module     After graph generation
                          relationships and       
                          cycles                  

  Visual Context          Upload and inspect      After an analysis
                          screenshots             exists

  Reports                 Review and export the   After an analysis
                          analysis report         exists

  Repository              View repository and     Always
                          branch metadata; start  
                          another analysis        
  -----------------------------------------------------------------------

The MVP may render these as tabs or sidebar links. Avoid implementing
multiple independent pages if a single analysis workspace with nested
routes is faster.

### 3.2 Global application regions

**A. Top bar** - CodeImpact wordmark - Current repository name and
branch - Analysis status badge - "New analysis" action - Optional
help/about entry

**B. Primary navigation** - Overview - Findings - Dependency Graph -
Visual Context - Reports

**C. Main workspace** - Page title and short explanatory subtitle -
Contextual controls - Main content region

**D. Global feedback region** - Toast notifications for short
success/error feedback - Inline alerts for persistent or actionable
issues - Job progress panel while analysis is running

### 3.3 Route design

Suggested client routes:

  Route                                         Screen
  --------------------------------------------- --------------------------
  `/`                                           Repository connection
  `/analysis/:analysisId`                       Overview
  `/analysis/:analysisId/findings`              Findings explorer
  `/analysis/:analysisId/findings/:findingId`   Finding detail
  `/analysis/:analysisId/graph`                 Dependency graph
  `/analysis/:analysisId/visual-context`        Visual Context Inspector
  `/analysis/:analysisId/reports`               Report and export

If routing time is limited, the same screen structure can be implemented
with a selected-tab state while retaining the analysis ID in application
state.

------------------------------------------------------------------------

## 4. Screen-Level Design

## 4.1 Screen A --- Repository Connection

### Objective

Make the first action obvious and communicate the repository
restrictions before analysis begins.

### Layout

-   Centered content container with a concise product statement.
-   Repository URL input as the dominant control.
-   Branch input or branch selector, defaulting to the repository's
    default branch when available.
-   Primary button: **Analyse repository**.
-   Small supporting text: public repositories only; supported file
    types/languages; repository size and time limits.
-   Optional sample repository action for a reliable demo.

### Input behaviour

-   Trim whitespace.
-   Accept only HTTPS GitHub repository URLs in the MVP.
-   Reject malformed URLs, unsupported hosts, embedded credentials,
    query strings that do not belong to the supported URL form, and path
    traversal attempts.
-   Normalize trailing slash and `.git` suffix where supported.
-   Branch is optional; if omitted, use the default branch discovered
    from repository metadata.

### States

-   **Idle:** Empty input with concise example placeholder.
-   **Valid:** URL parsed and ready.
-   **Invalid:** Inline message adjacent to the input; preserve user
    input.
-   **Submitting:** Disable duplicate submission and show "Preparing
    repository...".
-   **Rejected:** Explain the actionable reason, such as private
    repository, unsupported host, inaccessible repository, or repository
    limit exceeded.

### Acceptance criteria

-   User can start an analysis without configuring AI.
-   Validation errors are understandable and do not expose stack traces.
-   No repository code is executed during retrieval or analysis.

## 4.2 Screen B --- Analysis Progress

### Objective

Show that work is progressing and make the pipeline understandable
without overwhelming the user with tool logs.

### Progress stages

1.  Validating repository
2.  Retrieving source files
3.  Detecting project and language
4.  Running static analysis
5.  Building dependency graph
6.  Collecting evidence and test candidates
7.  Calculating review risk
8.  Preparing results

### Design

-   A vertical stepper or compact horizontal progress tracker.
-   Current stage has a clear active state.
-   Completed stages use a check indicator.
-   Failed stages show a warning state and a short explanation.
-   Display elapsed time and a "Back to repository" action only if
    navigation will not cancel the job.

### Important behaviour

-   Do not invent percentage completion if the backend cannot calculate
    it. Use stage-based progress instead.
-   Poll job status at a controlled interval with backoff.
-   If a non-critical analyser fails, show partial analysis and identify
    the missing tool output.
-   If a required stage fails, show retry guidance where retry is safe.

## 4.3 Screen C --- Repository Overview

### Objective

Give the developer a quick, credible summary and point to the next
useful action.

### Header

-   Repository owner/name
-   Branch and commit identifier if available
-   Language/project indicators
-   Analysis timestamp
-   Status badge: Complete, Partial, Failed

### Summary metric cards

Recommended cards: - Findings detected - Higher review-risk findings -
Dependency cycles - Duplicate-code groups - Test candidates identified

Do not label the total as a universal "code quality score" unless a
defensible scoring model is explicitly implemented. A metric card must
be traceable to a count or calculation.

### Main content

**Finding distribution** - Horizontal bar or compact chart grouped by
category. - Click a category to open Findings with that filter applied.

**Review-risk distribution** - Lower, Medium, Higher, and Unknown. - Add
a tooltip or short caption explaining that risk means review priority,
not probability of safe deletion.

**Recommended next steps** - A small list generated from deterministic
findings: - Inspect high-impact orphan candidates. - Review circular
dependencies. - Compare duplicate blocks. - Validate test candidates
before changing code.

**Analysis limitations** - Show missing or incomplete analyser
coverage. - Display unsupported language/file count if available. -
Explain that static analysis may miss runtime/dynamic references.

### Empty and partial states

-   Zero findings: "No findings were returned by the configured checks"
    rather than "Your code is perfect."
-   Partial analysis: show available results and a visible
    partial-status banner.
-   Missing graph: keep graph navigation disabled or show a clear
    unavailable state.

## 4.4 Screen D --- Findings Explorer

### Objective

Let users locate, prioritise, and compare findings efficiently.

### Main layout

-   Page header and result count.
-   Search input.
-   Filter row.
-   Findings table/list.
-   Optional detail drawer on desktop.

### Filters

-   Category: unused export, unused file, unused dependency, duplicate
    code, circular dependency, orphan candidate, other.
-   Review risk: Higher, Medium, Lower, Unknown.
-   Evidence classification: Strong, Inconclusive, Contradictory.
-   Source tool.
-   File path.
-   Test candidates available: Yes/No.

### Table columns

  Column        Description
  ------------- ------------------------------------------
  Finding       Human-readable title and short summary
  Category      Finding type
  Location      File path and line range where available
  Evidence      Strong / Inconclusive / Contradictory
  Review risk   Higher / Medium / Lower / Unknown
  Source        Static analyser or internal rule

### Interaction

-   Clicking a row opens the finding detail page or side drawer.
-   Sorting should be deterministic and stable.
-   Search should match title, path, symbol, and category.
-   Filters should be combinable.
-   Preserve filters when navigating back from a finding.

### Finding row design

-   Use a restrained category icon or text label.
-   Avoid emoji as primary status indicators.
-   Use text labels alongside colour.
-   Truncate long paths visually but expose full path on hover/focus and
    in details.

## 4.5 Screen E --- Finding Detail

### Objective

Explain what was detected, what evidence exists, what remains uncertain,
and what a developer should verify.

### Recommended layout

**1. Finding header** - Finding title - Category badge - Review-risk
badge - Evidence classification - File path and line range - Source tool

**2. What was detected** - Concise deterministic description. - Separate
raw analyser observation from application interpretation.

**3. Evidence** Present evidence as individual rows/cards: - Direct
references found - Importers/dependants - Entry-point relationship -
Dynamic import indicators - Framework/configuration indicators - Related
tests - Coverage information, if supplied - Tool output reference

Each evidence item should include a source or method and a clear value
such as "Found", "Not found by configured scan", "Unknown", or "Not
checked".

**4. Impact context** - Direct dependants - Upstream/downstream graph
relationships - Entry-point proximity - Related test candidates -
Potential affected files

**5. Uncertainty and limitations** Examples: - "No static reference was
found. Runtime-generated imports may not be visible to this analysis." -
"Test mapping is heuristic and does not establish complete test
coverage." - "This finding is a review candidate, not a deletion
instruction."

**6. AI explanation** - Explain the evidence in plain language. - State
why the finding may matter. - Identify false-positive scenarios. -
Recommend verification steps. - Never add unverified repository facts.

**7. Actions** - Explain with AI - View in dependency graph - View
related tests - Generate patch proposal (optional/stretch) - Copy
finding summary

### Evidence wording rules

Use: - "No reference was found by the configured static scan." - "No
matching test was identified by the current heuristic." - "The
repository evidence is inconclusive."

Avoid: - "This code is definitely unused." - "Safe to delete." - "No
tests exist" unless a complete and reliable test inventory proves it.

## 4.6 Screen F --- Dependency Graph

### Objective

Help users understand module relationships and circular dependencies.

### Layout

-   Graph canvas occupying most of the screen.
-   Left-side controls or toolbar for search, filters, and layout.
-   Right-side details panel for selected node or edge.
-   Legend explaining node/edge semantics.

### Graph semantics

-   Node = file or module.
-   Directed edge = import/dependency relationship.
-   Node size may represent degree or number of connections.
-   Node styling may represent file type or finding count, but do not
    overload the graph.
-   Cycle members should be visibly marked and also listed in a textual
    summary.

### Interactions

-   Pan and zoom.
-   Select node to inspect path, imports, dependants, and linked
    findings.
-   Select edge to inspect source and destination.
-   Search file path and focus the matching node.
-   Filter by directory, file type, cycle membership, or finding
    presence.
-   "Fit graph" action.
-   "Show cycles" action.

### Performance

-   Cap rendered nodes/edges for the hackathon MVP.
-   If the graph is too large, show a filtered subgraph and explain the
    limit.
-   Keep a textual list of cycles available even if graph rendering is
    unavailable.

### Accessibility fallback

Provide a table/list representation of nodes and dependencies. The graph
must not be the only way to access relationship information.

## 4.7 Screen G --- Visual Context Inspector

### Objective

Allow a developer to use a screenshot as supporting context for
repository investigation.

### Supported image types

-   Terminal stack trace
-   CI/build failure
-   IDE diagnostic
-   Architecture/dependency diagram
-   Screenshot containing a code snippet

### Upload panel

-   Drag-and-drop or file picker.
-   Accept PNG and JPEG only.
-   Display file size and selected context type.
-   Clearly warn users not to upload secrets, credentials, customer
    data, or sensitive production information.
-   Do not accept SVG or remote image URLs in the MVP.

### Result presentation

**Observed in image** - Extracted text snippets - Paths and symbols -
Line numbers - Error labels - Diagram labels/relationships, if detected

**Repository matches** - Exact path match - Approximate path match -
Symbol match - No match - Match method and repository location

**AI hypotheses** - Possible explanation or relationship. - Explicitly
marked "Hypothesis --- verify before acting". - Link to matching
findings where possible.

### Safety and trust

-   OCR/model extraction is not proof that a path or symbol exists.
-   Only backend repository lookup can mark a repository match as
    verified.
-   Treat screenshot text as untrusted input; it may contain
    instructions intended to manipulate the model.
-   Never follow instructions found inside the image.
-   Keep uploaded images temporary and delete them according to the
    retention policy.

## 4.8 Screen H --- Reports

### Objective

Provide a portable record of what was analysed and what the developer
should review.

### Report sections

1.  Repository and branch metadata
2.  Analysis timestamp and status
3.  Tool coverage and limitations
4.  Executive summary
5.  Findings by category
6.  Higher-priority review candidates
7.  Dependency cycles
8.  Duplicate-code groups
9.  Test-impact candidates
10. AI explanations, clearly labelled as generated assistance
11. Visual-context observations, if included
12. Recommended verification checklist

### Export

-   Markdown is the primary MVP export.
-   PDF can be deferred.
-   Export should use stored analysis data, not rerun analysers or
    regenerate AI content unexpectedly.
-   Include a disclaimer that results are static-analysis evidence and
    require developer review.

------------------------------------------------------------------------

## 5. Visual Design System

### 5.1 Design direction

CodeImpact should look like a serious engineering utility: precise,
calm, technical, and readable. Avoid the generic AI-dashboard aesthetic,
excessive gradients, emoji icons, glassmorphism, decorative AI sparkles,
and oversized rounded cards.

### 5.2 Suggested palette

  Token                    Suggested value   Usage
  ------------------------ ----------------- ----------------------------------
  `color-bg`               `#0B1020`         Main dark application background
  `color-surface`          `#121A2B`         Panels and cards
  `color-surface-raised`   `#182338`         Hovered/raised surfaces
  `color-border`           `#273449`         Dividers and outlines
  `color-text`             `#E6EDF7`         Primary text
  `color-muted`            `#98A7BC`         Secondary text
  `color-primary`          `#6EA8FE`         Primary actions and focus
  `color-success`          `#39B980`         Completed/positive state
  `color-warning`          `#E6B450`         Medium risk and caution
  `color-danger`           `#E16B72`         Higher risk or errors
  `color-info`             `#65B8C8`         Informational state

The palette is a starting point. Check contrast before finalising.

### 5.3 Typography

-   Use a modern sans-serif for UI text, such as Inter or system UI.
-   Use a monospace font for file paths, symbols, code, line numbers,
    and technical identifiers.
-   Establish a clear type scale:
    -   Page title: 24--30 px
    -   Section title: 16--20 px
    -   Body: 14--16 px
    -   Metadata: 12--13 px
-   Avoid low-contrast microtext for critical evidence or warnings.

### 5.4 Spacing and layout

Use a consistent 4 px base spacing scale (4, 8, 12, 16, 24, 32, 40).
Prefer a small number of layout primitives over one-off spacing values.

-   Desktop content max width: approximately 1440 px.
-   Main workspace horizontal padding: 24--32 px.
-   Card padding: 16--20 px.
-   Table row height: 52--64 px depending on density.
-   Keep the repository overview information-dense but not cramped.

### 5.5 Shape and elevation

-   Use modest corner radii: 6--10 px.
-   Use borders and subtle elevation rather than heavy shadows.
-   Reserve strong accent treatment for primary actions and active
    navigation.
-   Do not use gradients as the default panel background.

### 5.6 Iconography

-   Use one consistent outline icon family, such as Lucide.
-   Icons must have a clear meaning and consistent stroke weight.
-   Pair unfamiliar icons with text labels.
-   Do not use emoji as functional navigation or status icons.

### 5.7 Status and risk colours

Colour must never be the only signal. Always show a text label.

  -----------------------------------------------------------------------
  State                   Label                   Visual treatment
  ----------------------- ----------------------- -----------------------
  Lower review risk       Lower                   Muted green/neutral
                                                  badge

  Medium review risk      Medium                  Amber badge

  Higher review risk      Higher                  Red badge

  Unknown                 Unknown                 Grey outlined badge

  Strong evidence         Strong                  Text + restrained
                                                  positive indicator

  Inconclusive evidence   Inconclusive            Text + neutral/amber
                                                  indicator

  Contradictory evidence  Contradictory           Text + warning
                                                  indicator
  -----------------------------------------------------------------------

Review risk is a prioritisation aid, not a probability that a change is
safe.

------------------------------------------------------------------------

## 6. Component Design

### 6.1 Shared frontend components

  Component                 Responsibility
  ------------------------- -----------------------------------------------
  `AppShell`                Global layout, top bar, navigation, workspace
  `RepositoryForm`          URL/branch input and validation
  `AnalysisStatus`          Job state and stage progress
  `MetricCard`              Single traceable summary metric
  `FilterBar`               Search and combined filters
  `FindingsTable`           Sortable and selectable findings
  `FindingBadge`            Category, evidence, and risk labels
  `EvidenceList`            Evidence rows with source and status
  `ImpactPanel`             Dependants, graph context, test candidates
  `AIExplanationPanel`      Structured explanation and limitations
  `DiffViewer`              Read-only patch proposal display
  `DependencyGraph`         Interactive module graph
  `GraphDetailsPanel`       Selected node/edge information
  `ImageUploadPanel`        Secure PNG/JPEG upload interface
  `VisualObservationCard`   Extracted image observation
  `RepositoryMatchCard`     Backend-verified repository match
  `HypothesisCard`          AI-generated, unverified interpretation
  `ReportPreview`           Markdown report preview/export
  `EmptyState`              Context-specific no-data messaging
  `ErrorState`              Actionable failure messaging
  `Toast`                   Brief transient feedback

### 6.2 Component behaviour rules

-   Components receive typed data through props; avoid hidden global
    dependencies.
-   Loading, empty, partial, error, and success states should be
    explicit.
-   Use skeletons only when the layout is known; otherwise use a compact
    progress state.
-   Long-running analysis state belongs in a central analysis/job store.
-   Avoid duplicate API requests when switching tabs.
-   Use stable IDs for findings and graph nodes.

### 6.3 Suggested frontend state

``` ts
type AnalysisStatus =
  | "queued"
  | "running"
  | "completed"
  | "partial"
  | "failed";

type EvidenceClass =
  | "strong"
  | "inconclusive"
  | "contradictory";

type ReviewRisk =
  | "lower"
  | "medium"
  | "higher"
  | "unknown";

interface AnalysisSummary {
  analysisId: string;
  repository: string;
  branch: string;
  commitSha?: string;
  status: AnalysisStatus;
  createdAt: string;
  completedAt?: string;
  metrics: {
    totalFindings: number;
    higherRisk: number;
    mediumRisk: number;
    lowerRisk: number;
    unknownRisk: number;
    circularDependencies: number;
    duplicateGroups: number;
    testCandidates: number;
  };
}
```

------------------------------------------------------------------------

## 7. Backend Design and Service Boundaries

### 7.1 Logical architecture

``` text
┌──────────────────────────────────────────────────────┐
│                    React Frontend                    │
│ Repository Form | Overview | Findings | Graph        │
│ Visual Context | AI Explanation | Reports            │
└──────────────────────────┬───────────────────────────┘
                           │ HTTPS / JSON / Multipart
┌──────────────────────────▼───────────────────────────┐
│                    FastAPI Backend                   │
│                                                      │
│ API Router                                           │
│   ├── Repository / Analysis API                      │
│   ├── Findings / Graph API                           │
│   ├── AI Explanation / Patch API                     │
│   ├── Visual Context API                             │
│   └── Report API                                     │
│                                                      │
│ Application Services                                 │
│   ├── Analysis Orchestrator                          │
│   ├── Repository Retrieval                           │
│   ├── Static Analyzer Runners                        │
│   ├── Finding Normalizer                             │
│   ├── Dependency Graph Service                       │
│   ├── Evidence Collector                             │
│   ├── Review Risk Engine                             │
│   ├── Test Impact Mapper                             │
│   ├── AI Inference Orchestrator                      │
│   ├── Visual Context Service                         │
│   └── Report Builder                                 │
│                                                      │
│ Temporary Workspace + Analysis Store                │
└──────────────────────────────────────────────────────┘
```

### 7.2 Service responsibilities

**Repository Retrieval Service** - Validate and normalize repository
input. - Retrieve repository metadata and source files. - Enforce file
count, size, and time limits. - Never execute repository code or
lifecycle scripts. - Create a temporary workspace and clean it after
processing.

**Analysis Orchestrator** - Create analysis ID and job state. - Execute
stages in a defined order. - Capture tool output and errors. - Permit
partial completion when a non-critical analyser fails. - Persist
normalised results.

**Static Analyzer Runners** - Wrap Knip, jscpd, Madge, and optional
ESLint. - Invoke subprocesses with explicit arguments, `shell=False`,
bounded output, and timeouts. - Normalize tool-specific output before
passing it downstream.

**Finding Normalizer** - Convert different tool outputs into one
`Finding` schema. - Preserve original tool name and raw evidence
references. - Deduplicate only when there is a defensible identity rule.

**Dependency Graph Service** - Build directed file/module
relationships. - Detect cycles and compute graph neighbourhoods. -
Provide bounded graph responses for the frontend.

**Evidence Collector** - Attach direct references, dependants,
entry-point indicators, dynamic usage indicators, test candidates, and
available coverage context. - Distinguish "not found" from "not
checked".

**Review Risk Engine** - Apply transparent deterministic rules. - Return
risk label and factor breakdown. - Do not produce a probability of safe
deletion.

**AI Inference Orchestrator** - Use Gemma 4 as the primary inference
route. - Apply timeout, retry, and automatic secondary inference when
required. - Normalize all model responses into the same application
schema. - Keep provider selection and provider-specific details out of
user-facing UI and public product documentation. - If all inference
routes fail, return a deterministic explanation assembled from known
evidence.

**Visual Context Service** - Validate image type, signature, size, and
request context. - Send image and bounded repository context to AI
inference. - Parse structured observations. - Verify extracted paths and
symbols against repository inventory. - Mark hypotheses separately from
verified matches.

**Report Builder** - Build Markdown from persisted analysis results. -
Include limitations and tool coverage. - Do not silently regenerate AI
explanations during export.

### 7.3 Dependency direction

Keep the dependency direction inward:

-   API routers call application services.
-   Application services call analyzer, storage, and AI adapters.
-   Analyzer adapters do not import API routers.
-   AI adapters do not access the frontend or manipulate repository
    files.
-   Schemas are shared contracts and should not contain service
    execution logic.

------------------------------------------------------------------------

## 8. Data Design

### 8.1 Core entities

**Analysis** - `analysis_id` - `repository_url` -
`repository_full_name` - `branch` - `commit_sha` - `status` -
`current_stage` - `created_at` - `completed_at` - `tool_coverage` -
`error_summary`

**Finding** - `finding_id` - `analysis_id` - `category` - `title` -
`description` - `file_path` - `start_line` - `end_line` - `symbol` -
`source_tool` - `evidence_class` - `review_risk` - `risk_factors` -
`evidence` - `created_at`

**Dependency** - `analysis_id` - `source_file` - `target_file` -
`relationship` - `source_tool`

**TestCandidate** - `analysis_id` - `finding_id` - `test_path` -
`mapping_reason` - `mapping_strength`

**AIExplanation** - `explanation_id` - `analysis_id` - `finding_id` -
`summary` - `why_it_matters` - `false_positive_scenarios` -
`verification_steps` - `suggested_action` - `model_route_metadata`
(internal operational metadata only; never exposed in public UI)

**VisualContext** - `visual_context_id` - `analysis_id` -
`context_type` - `observations` - `repository_matches` - `hypotheses` -
`created_at` - `image_retention_state`

**PatchProposal** - `patch_id` - `analysis_id` - `finding_id` -
`unified_diff` - `rationale` - `validation_notes` - `status`
(proposed/reviewed/rejected)

### 8.2 Evidence representation

Every evidence item should contain:

``` json
{
  "kind": "direct_reference",
  "status": "not_found",
  "value": 0,
  "source": "repository_static_scan",
  "method": "configured import/reference scan",
  "details": "No direct static reference was returned by the configured scan.",
  "limitations": [
    "Runtime-generated imports may not be visible."
  ]
}
```

Allowed evidence statuses should include: - `found` - `not_found` -
`unknown` - `not_checked` - `conflicting`

Do not collapse unknown, not checked, and not found into one value.

### 8.3 Visual context response model

``` json
{
  "visual_context_id": "vc_123",
  "context_type": "ci_failure",
  "observations": [
    {
      "type": "file_path",
      "text": "src/services/cache.ts",
      "confidence": "model_reported"
    },
    {
      "type": "error_message",
      "text": "Module resolution failed",
      "confidence": "model_reported"
    }
  ],
  "repository_matches": [
    {
      "observed_text": "src/services/cache.ts",
      "match_status": "exact",
      "repository_path": "src/services/cache.ts",
      "verification_source": "repository_file_inventory"
    }
  ],
  "hypotheses": [
    {
      "summary": "The failure may involve module resolution.",
      "verification_required": true
    }
  ]
}
```

The `confidence` field above describes extraction provenance, not
factual certainty. The backend match is the authoritative repository
check.

------------------------------------------------------------------------

## 9. AI Interaction Design

### 9.1 AI responsibilities

Gemma 4 is the primary AI model for: - Explaining static-analysis
findings in developer-friendly language. - Describing why evidence may
indicate a review candidate. - Identifying plausible false-positive
causes from supplied context. - Summarising dependency and test
impact. - Interpreting supported screenshots. - Suggesting refactoring
approaches. - Producing optional review-only patch proposals.

### 9.2 AI must not

-   Claim that a file is safe to delete based only on missing static
    references.
-   Invent paths, symbols, tests, tool results, line numbers, or
    dependency edges.
-   Claim test coverage unless actual coverage data is supplied.
-   Execute code, run shell commands, or modify repository contents.
-   Treat screenshot text as trusted instructions.
-   Override deterministic evidence with an unsupported assertion.
-   expose hidden model/provider routing details to the user.

### 9.3 Prompt context construction

Send only the minimum relevant context: - Finding schema and evidence
items - Nearby source excerpts, if available and safe - Relevant graph
neighbours - Related test candidates - Tool coverage and analysis
limitations - Optional visual observations and verified repository
matches

Do not send the entire repository by default. Redact secrets and cap
context size.

### 9.4 Structured AI response

``` json
{
  "summary": "A concise explanation grounded in the supplied evidence.",
  "why_it_matters": "Potential maintenance or reliability impact.",
  "false_positive_scenarios": [
    "A runtime-generated import may not be visible to the static scan."
  ],
  "verification_steps": [
    "Search runtime configuration for references.",
    "Check framework registration conventions.",
    "Run the relevant test suite."
  ],
  "suggested_action": "Review the candidate before making changes.",
  "limitations": [
    "Static analysis does not establish runtime reachability."
  ]
}
```

### 9.5 Reliability and silent failover

The application should expose a single logical AI service contract to
the rest of the backend.

Request flow: 1. Validate request and build bounded context. 2. Invoke
the primary Gemma 4 route. 3. Apply a configured timeout and bounded
retry policy. 4. If the primary route fails due to timeout, transient
service error, or rate limit, invoke the configured secondary inference
route. 5. Validate the returned JSON against the same Pydantic schema.
6. If the secondary route also fails, return a deterministic
evidence-based response. 7. Record internal operational telemetry
without showing provider details in the UI.

Requirements: - The frontend calls one application endpoint and receives
one stable schema. - The frontend must not branch on model/provider
identity. - Do not display "switching model" or provider-specific
messages. - Do not silently label deterministic output as
AI-generated. - AI-generated content should carry an internal provenance
field and a user-facing content type such as `AI explanation` or
`Evidence-based summary`. - Do not retry non-idempotent operations
without an idempotency strategy. - Use bounded timeouts and avoid retry
storms. - Store model/provider routing information only in restricted
operational logs/configuration where necessary.

### 9.6 User-facing failure states

If inference is unavailable: - Keep the deterministic finding evidence
visible. - Display: "AI explanation is temporarily unavailable. You can
still review the evidence and analysis results." - Do not expose
technical credentials, provider names, stack traces, or raw upstream
errors. - Allow the user to retry.

------------------------------------------------------------------------

## 10. Interaction and State Design

### 10.1 Global states

Every data-driven screen should support: - Initial - Loading - Success -
Empty - Partial - Error - Stale data

### 10.2 Analysis lifecycle

``` text
CREATED
  |
  v
QUEUED
  |
  v
RUNNING
  |-----------------------------|
  |                             |
  v                             v
COMPLETED                    PARTIAL
  |
  v
AVAILABLE FOR REVIEW

Any required-stage failure may transition to FAILED.
```

A partial result must list which stages/tools did not complete.

### 10.3 Finding lifecycle

Findings are analysis observations, not workflow commands. Optional user
review state may be added:

-   `unreviewed`
-   `reviewing`
-   `accepted_for_followup`
-   `dismissed`
-   `resolved_externally`

Do not equate "dismissed" with "false positive" unless the user
explicitly records that reason.

### 10.4 Confirmation rules

-   Starting analysis: one explicit action.
-   Uploading screenshot: user-selected file and explicit upload action.
-   Generating a patch proposal: explicit user action.
-   Applying a patch: not part of the MVP.
-   Deleting files, committing, pushing, or opening a pull request: not
    part of the MVP.

------------------------------------------------------------------------

## 11. API and Frontend Contract

The API specification in the TRD remains authoritative. The following is
the design-level contract.

  -------------------------------------------------------------------------------------------
  Endpoint                                    Method                  Purpose
  ------------------------------------------- ----------------------- -----------------------
  `/api/repositories/analyse`                 POST                    Start repository
                                                                      analysis

  `/api/analyses/{id}`                        GET                     Get analysis status and
                                                                      summary

  `/api/analyses/{id}/findings`               GET                     List/filter findings

  `/api/analyses/{id}/graph`                  GET                     Retrieve dependency
                                                                      graph

  `/api/analyses/{id}/findings/{findingId}`   GET                     Retrieve finding detail

  `/api/analyses/{id}/explain`                POST                    Generate structured
                                                                      explanation

  `/api/analyses/{id}/patch`                  POST                    Generate review-only
                                                                      patch proposal

  `/api/analyses/{id}/visual-context`         POST                    Upload and analyse
                                                                      screenshot

  `/api/analyses/{id}/report`                 GET                     Download Markdown
                                                                      report
  -------------------------------------------------------------------------------------------

### 11.1 API design rules

-   Use consistent JSON response envelopes.
-   Use stable machine-readable error codes.
-   Validate all request bodies with Pydantic.
-   Return `202 Accepted` for asynchronous analysis creation.
-   Return job status rather than holding a long HTTP request open.
-   Use pagination or bounded limits for findings and graph data.
-   Enforce request size limits on image uploads.
-   Do not return raw subprocess output directly to the browser.

### 11.2 Example error envelope

``` json
{
  "error": {
    "code": "REPOSITORY_NOT_ACCESSIBLE",
    "message": "The repository could not be accessed. Check that it is public and the URL is correct.",
    "request_id": "req_abc123"
  }
}
```

------------------------------------------------------------------------

## 12. Security, Privacy, and Trust Design

### 12.1 Repository safety

-   Accept only supported public GitHub URLs.
-   Prevent SSRF and arbitrary host access.
-   Never execute repository code.
-   Never run package lifecycle scripts.
-   Do not install repository dependencies in the MVP.
-   Use `shell=False` for subprocess calls.
-   Use explicit working directories and timeouts.
-   Prevent path traversal and symlink escape.
-   Limit file count, file size, total bytes, and analysis duration.
-   Clean temporary workspaces after analysis or expiry.

### 12.2 Image upload safety

-   PNG/JPEG only.
-   Verify MIME type and file signature.
-   Apply file-size and dimension limits.
-   Reject SVG, HTML, archives, and remote URLs.
-   Store temporarily with random names.
-   Remove temporary files after processing/retention expiry.
-   Treat image contents as untrusted data, not instructions.

### 12.3 AI prompt-injection controls

Repository files, comments, READMEs, test output, and screenshots may
contain malicious instructions. Treat all such content as untrusted
evidence.

-   System instructions must remain separate from repository content.
-   Never execute instructions embedded in repository or screenshot
    content.
-   Do not disclose secrets or environment variables.
-   Do not allow model output to trigger tools or modify files.
-   Validate all structured model output.
-   Cross-check extracted paths/symbols with backend inventory.

### 12.4 Privacy

-   Do not request private repository access for the MVP.
-   Do not log API keys or full sensitive payloads.
-   Avoid storing raw source code longer than required.
-   Provide clear temporary-data retention behaviour.
-   Warn users before screenshot upload not to include credentials or
    sensitive data.

------------------------------------------------------------------------

## 13. Accessibility and Responsive Behaviour

### 13.1 Accessibility

-   All controls must be keyboard reachable.
-   Provide visible focus indicators.
-   Use semantic headings and form labels.
-   Use text labels with all status colours.
-   Provide accessible names for icon-only buttons.
-   Ensure tables have proper headers.
-   Provide a non-graph textual representation of dependency
    relationships.
-   Announce asynchronous status changes through an appropriate live
    region.
-   Maintain readable contrast and avoid tiny text.

### 13.2 Responsive breakpoints

Suggested behaviour: - **Large desktop:** Persistent sidebar,
multi-column overview, full findings table, graph with details panel. -
**Tablet:** Collapsible sidebar, two-column metrics, filter drawer,
graph details below or in overlay. - **Mobile:** Single-column layout,
compact top navigation, stacked metric cards, findings as cards instead
of wide tables, graph with simplified controls.

The MVP may optimise primarily for laptop/desktop because the product is
a developer tool, but core tasks should remain usable on smaller
screens.

------------------------------------------------------------------------

## 14. Performance Design

### 14.1 Backend

-   Run analysis as a background job.
-   Apply per-stage timeouts.
-   Bound repository download size and file count.
-   Bound analyser stdout/stderr capture.
-   Avoid repeated parsing of the same file.
-   Cache analysis results by repository, commit, branch, and
    configuration only if cache correctness is reliable.
-   Return paginated findings.
-   Return a bounded graph subview when the full graph is too large.

### 14.2 Frontend

-   Fetch overview summary separately from detailed findings.
-   Load finding evidence on demand.
-   Lazy-load graph and visual-context screens.
-   Debounce search input.
-   Avoid re-rendering the entire graph when unrelated UI state changes.
-   Display progress rather than freezing the page.

### 14.3 AI

-   Keep prompts concise and evidence-focused.
-   Avoid sending full repository contents.
-   Set request timeout and output token limits.
-   Use structured output and schema validation.
-   Use bounded retries and automatic failover.
-   Use deterministic output when inference is unavailable.

------------------------------------------------------------------------

## 15. Observability and Diagnostics

Internal logs should support debugging without leaking source code or
secrets.

### Required events

-   Analysis created
-   Repository retrieval started/completed/failed
-   Analyser started/completed/failed
-   Graph generated
-   Evidence/risk calculation completed
-   AI request started/completed/failed
-   Automatic inference failover triggered
-   Visual context upload accepted/rejected
-   Report generated

### Suggested telemetry fields

-   `request_id`
-   `analysis_id`
-   `stage`
-   `duration_ms`
-   `status`
-   `error_code`
-   `file_count`
-   `finding_count`
-   `inference_attempt`
-   `response_schema_valid`

Do not log API keys, authentication headers, full source files, or
unredacted screenshots.

------------------------------------------------------------------------

## 16. Testing Strategy

### 16.1 Unit tests

-   Repository URL validation and normalization
-   Finding normalisation
-   Evidence status handling
-   Review-risk rules
-   Dependency graph construction and cycle detection
-   Test-candidate mapping
-   AI response schema validation
-   Screenshot path/symbol verification
-   Report generation

### 16.2 Integration tests

-   Public repository retrieval
-   Static analyser invocation and timeout handling
-   Partial analysis when an optional tool fails
-   End-to-end finding detail retrieval
-   Dependency graph API
-   AI primary success path
-   Primary timeout followed by secondary inference
-   Both inference routes failing and deterministic response returned
-   Image upload validation and visual-context response
-   Markdown report export

### 16.3 Frontend tests

-   Repository form validation
-   Analysis progress state
-   Findings filters and sorting
-   Finding detail evidence rendering
-   Risk and evidence labels
-   Graph selection and textual fallback
-   Visual Context three-section rendering
-   AI unavailable state
-   Responsive navigation

### 16.4 Security tests

-   Non-GitHub URL rejection
-   URL parsing edge cases
-   Path traversal attempts
-   Symlink escape attempts
-   Oversized repository and image rejection
-   Invalid image signature rejection
-   Malicious text in screenshot/repository fixtures
-   Subprocess timeout and output cap
-   Secret redaction checks

------------------------------------------------------------------------

## 17. Recommended Implementation Structure

``` text
codeimpact/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── overview/
│   │   │   ├── findings/
│   │   │   ├── graph/
│   │   │   ├── visual-context/
│   │   │   └── shared/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── store/
│   │   ├── types/
│   │   └── styles/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── repository_service.py
│   │   │   ├── analysis_orchestrator.py
│   │   │   ├── finding_normalizer.py
│   │   │   ├── dependency_graph_service.py
│   │   │   ├── evidence_service.py
│   │   │   ├── risk_engine.py
│   │   │   ├── test_impact_service.py
│   │   │   ├── ai_orchestrator.py
│   │   │   ├── visual_context_service.py
│   │   │   └── report_service.py
│   │   ├── analyzers/
│   │   ├── adapters/
│   │   ├── jobs/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
│
├── fixtures/
│   ├── repositories/
│   ├── analyser_outputs/
│   └── screenshots/
│
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   └── DESIGN.md
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

This structure is a target layout, not a requirement to create every
folder during the five-hour build. Keep the MVP compact while preserving
clear service boundaries.

------------------------------------------------------------------------

## 18. Five-Hour Design-to-Build Priorities

  -----------------------------------------------------------------------
  Priority                Deliverable             Why it matters
  ----------------------- ----------------------- -----------------------
  P0                      Repository form,        Complete end-to-end
                          analysis orchestration, product flow
                          findings list           

  P0                      Evidence and risk       Core product
                          labels                  differentiation and
                                                  trust

  P0                      Gemma explanation with  Demonstrates primary AI
                          common response schema  capability

  P1                      Overview dashboard and  Makes results
                          Markdown report         judge-friendly

  P1                      Dependency graph and    Strong visual
                          cycle summary           demonstration

  P1                      Visual Context          Distinct multimodal use
                          Inspector with          case
                          repository cross-check  

  P2                      Patch proposal diff     Useful but not
                          viewer                  essential

  P2                      Advanced graph layouts, Defer beyond MVP
                          coverage integrations,  
                          multi-language support  
  -----------------------------------------------------------------------

### Five-hour implementation sequence

1.  **0--30 min:** Create app shell, API skeleton, and verify primary AI
    access.
2.  **30--75 min:** Implement repository validation and retrieval.
3.  **75--135 min:** Integrate static analysis and normalise findings.
4.  **135--170 min:** Build dependency graph and cycle summary.
5.  **170--200 min:** Add evidence collection and review-risk rules.
6.  **200--225 min:** Add AI explanation and inference failover.
7.  **225--250 min:** Add Visual Context upload, extraction, and
    repository matching.
8.  **250--280 min:** Complete overview, finding details, and report
    export.
9.  **280--300 min:** Test the demo path, handle errors, and polish.

If time is short, reduce the number of finding categories and graph
complexity. Do not remove evidence transparency, human approval, or the
AI response validation path.

------------------------------------------------------------------------

## 19. Demo Design

### 19.1 Demo setup

Prepare a known public JavaScript/TypeScript repository or a small
controlled fixture repository with: - At least one unused export or
dependency candidate. - A duplicate-code example. - A circular
dependency if practical. - A test file that can be mapped to a source
file. - A screenshot of a representative CI or terminal error.

Do not rely on a live repository with unpredictable structure as the
only demo input. Keep a local fixture or precomputed analysis available
as a backup, clearly labelled as a fixture.

### 19.2 Suggested demo sequence

1.  Paste repository URL and start analysis.
2.  Show progress stages.
3.  Open overview and explain the metrics.
4.  Filter findings to higher review-risk items.
5.  Open one finding and walk through evidence and uncertainty.
6.  Ask Gemma 4 for a grounded explanation.
7.  Open dependency graph and show a cycle or dependency relationship.
8.  Upload a CI screenshot in Visual Context.
9.  Show extracted observations, repository-verified matches, and
    hypotheses separately.
10. Export the Markdown report.

### 19.3 Core demo message

"CodeImpact does not just flag suspicious code. It connects
static-analysis output with dependency and test evidence, explains
uncertainty, and helps developers decide what to review next. AI assists
with interpretation, but developers stay in control of every change."

------------------------------------------------------------------------

## 20. Design Decisions and Rationale

  -----------------------------------------------------------------------
  Decision                            Rationale
  ----------------------------------- -----------------------------------
  Evidence and AI explanation are     Prevents generated interpretation
  separate UI sections                from appearing as raw fact

  Risk is categorical, not a          Avoids false precision
  deletion-safety percentage          

  Findings are review candidates      Static analysis cannot prove all
                                      runtime behaviour

  Primary and secondary inference     Keeps frontend stable and supports
  share one schema                    reliability

  Provider details are hidden from    Keeps the product experience
  user-facing surfaces                provider-agnostic

  Screenshot observations are         Prevents model-extracted paths from
  cross-checked by backend            being treated as verified

  Patch output is a read-only diff    Preserves developer control

  Markdown is the first report format Fast, portable, easy to inspect in
                                      a hackathon

  Public repositories only in MVP     Reduces authentication and privacy
                                      complexity

  No repository code execution        Reduces risk from untrusted
                                      projects
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 21. Definition of Done

The design is considered implemented when:

### Product flow

-   [ ] A user can submit a supported public GitHub repository.
-   [ ] The analysis job reports meaningful stages.
-   [ ] Completed or partial analysis results are accessible.
-   [ ] The overview displays traceable metrics.
-   [ ] Findings can be searched, filtered, sorted, and opened.

### Evidence and safety

-   [ ] Each finding has evidence and source metadata.
-   [ ] Unknown and not-checked states are not misrepresented as
    not-found.
-   [ ] Risk labels include explanatory factors.
-   [ ] No UI claims that a candidate is safe to delete.
-   [ ] No automatic repository modifications occur.

### AI and reliability

-   [ ] Gemma 4 is configured as the primary model.
-   [ ] All inference routes conform to one validated response schema.
-   [ ] Timeout and automatic failover are implemented.
-   [ ] Deterministic output is available if inference is unavailable.
-   [ ] User-facing screens do not expose provider routing details.
-   [ ] AI explanations are grounded in supplied evidence.

### Visual Context

-   [ ] PNG/JPEG upload validation works.
-   [ ] Observations, verified matches, and hypotheses are visually
    distinct.
-   [ ] Extracted paths are checked against repository inventory.
-   [ ] Uploaded images are handled as untrusted input and cleaned up.

### Delivery

-   [ ] Dependency graph has a textual fallback.
-   [ ] Markdown report exports successfully.
-   [ ] Error, loading, empty, and partial states are present.
-   [ ] Core demo path has been tested end-to-end.

------------------------------------------------------------------------

## 22. Final Design Statement

CodeImpact is designed as an evidence-first developer investigation
workspace. It combines deterministic repository analysis, dependency
relationships, test-impact clues, transparent review-risk
classification, and AI-assisted explanations in one workflow. Its
interface must make a clear distinction between what tools observed,
what the backend verified, and what AI suggests.

The product should never imply that absence of a static reference proves
code is unused. It should help developers make better-informed decisions
while keeping all code changes under explicit human control.
