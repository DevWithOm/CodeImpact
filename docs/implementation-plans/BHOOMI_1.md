# BHOOMI_1 --- Frontend & UI/UX Implementation Plan

**Timebox:** 4 hours (240 minutes) \| **Environment:** Antigravity +
Gemini 3.8 Flash, Medium effort\
**Stack:** React, Vite, TypeScript, Tailwind CSS, React Flow\
**Deliverable:** Interactive frontend displaying real CodeImpact
analysis results.

## 1. Mission and Four-Hour Definition of Done

Build the repository input, analysis progress, dashboard, findings
explorer, finding detail, dependency graph, AI recommendation panel, and
report download interaction.

A successful MVP lets a developer: 1. Enter a public GitHub repository
URL and optional branch. 2. Start analysis and see real job status. 3.
View repository summary metrics. 4. Search/filter findings and open a
finding. 5. Inspect dependency graph nodes, edges and cycles. 6. Read
backend-generated AI explanations and recommendations.

**Do not build now:** authentication, user settings, complex animations,
source editing, automatic deletion, a generic chatbot, or elaborate
mobile graph interactions. Prioritise a complete working flow over
visual decoration.

## 2. API Contract --- Confirm with TANUJA_4

Use one API client module and typed interfaces. Until backend endpoints
are ready, use mock responses behind the same service functions; do not
scatter mock data across components.

  Method   Endpoint                                    Purpose
  -------- ------------------------------------------- --------------------
  POST     `/api/repositories/analyse`                 Start analysis
  GET      `/api/analyses/{id}`                        Status and summary
  GET      `/api/analyses/{id}/findings`               Findings list
  GET      `/api/analyses/{id}/findings/{findingId}`   Finding detail
  GET      `/api/analyses/{id}/graph`                  Dependency graph
  POST     `/api/analyses/{id}/explain`                AI explanation
  GET      `/api/analyses/{id}/report`                 Markdown report

### Start request / response

``` json
{
  "repository_url": "https://github.com/owner/repository",
  "branch": "main"
}
```

``` json
{
  "analysis_id": "an_demo123",
  "status": "queued",
  "repository": "owner/repository",
  "branch": "main"
}
```

### Normalised finding

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
  "review_risk": "medium",
  "evidence": [
    {
      "kind": "direct_reference",
      "status": "not_found",
      "source": "knip",
      "details": "No direct static reference was returned."
    }
  ],
  "risk_factors": ["Dynamic usage has not been ruled out."]
}
```

### Graph response

``` json
{
  "nodes": [
    {"id": "src/main.ts", "label": "main.ts", "file_path": "src/main.ts", "finding_count": 1, "cycle_member": false}
  ],
  "edges": [
    {"id": "src/main.ts->src/app.ts", "source": "src/main.ts", "target": "src/app.ts"}
  ],
  "cycles": [["src/a.ts", "src/b.ts"]]
}
```

### AI explanation

``` json
{
  "summary": "No static reference was found by the configured scan.",
  "why_it_matters": "The export may be unnecessary maintenance surface.",
  "false_positive_scenarios": ["The symbol may be loaded dynamically."],
  "verification_steps": ["Check runtime registration and dynamic imports."],
  "suggested_action": "Review before changing the export.",
  "limitations": ["Static analysis cannot prove runtime reachability."]
}
```

**Critical wording:** show *review risk*, not deletion-safety
probability. Never label code "safe to delete" based only on static
analysis.

## 3. Screens and Components

### Screens

1.  **Repository Connect:** GitHub URL, optional branch, Analyse button,
    public repository note.
2.  **Analysis Progress:** stage tracker, status, elapsed time; no
    fabricated percentage.
3.  **Overview:** repository metadata, metric cards, finding
    distribution, review-risk distribution, cycle summary, tool
    coverage.
4.  **Findings:** search, category/risk/evidence filters, sortable
    table.
5.  **Finding Detail:** description, evidence, risk factors, impact/test
    candidates, AI explanation and limitations.
6.  **Dependency Graph:** React Flow canvas, cycle highlighting,
    selected-node details.
7.  **Reports:** report preview/download.

### Suggested structure

``` text
src/
  app/                 # App, router
  components/
    layout/
    repository/
    analysis/
    overview/
    findings/
    graph/
    ai/
    shared/
  pages/
  services/api.ts
  services/mockApi.ts
  types/index.ts
  hooks/
  styles/
```

### Design direction

-   Professional developer-tool UI; no emoji icons or excessive
    gradients.
-   Use one outline icon family such as Lucide.
-   Suggested dark palette: `#0B1020` background, `#121A2B` surface,
    `#273449` border, `#E6EDF7` text, `#98A7BC` muted, `#6EA8FE`
    primary.
-   Always pair risk colours with text labels: Lower, Medium, Higher,
    Unknown.
-   Evidence labels: Strong, Inconclusive, Contradictory.
-   Keep file paths and symbols in a monospace font.

## 4. Four-Hour Execution Plan

  ------------------------------------------------------------------------
  Time                    Work                    Output
  ----------------------- ----------------------- ------------------------
  00--20 min              Scaffold Vite/React/TS, App runs
                          Tailwind, router, React 
                          Flow, icons             

  20--40                  App shell, navigation,  Consistent shell
                          page layout, design     
                          tokens                  

  40--65                  Repository form,        Submit flow
                          validation, start API   
                          call                    

  65--85                  Progress screen and     Job states
                          status polling          

  85--120                 Overview and metric     Dashboard
                          cards                   

  120--155                Findings table,         Findings workflow
                          filters, search, detail 

  155--190                React Flow graph, cycle Interactive graph
                          styling, node selection 

  190--210                AI explanation panel    Recommendations/report
                          and report download     

  210--230                Connect real API, fix   Integration
                          CORS and schema         
                          mismatches              

  230--240                Demo test, critical     Handoff
                          fixes, commit           
  ------------------------------------------------------------------------

If time slips: preserve repository submit → findings detail → overview →
graph → AI panel → polish. Do not sacrifice API integration for
decorative UI.

## 5. Implementation Rules

### API client

Create `api.ts` functions: - `startAnalysis(payload)` -
`getAnalysis(id)` - `getFindings(id, filters)` -
`getFinding(id, findingId)` - `getGraph(id)` -
`explainFinding(id, findingId)` - `downloadReport(id)`

Use `VITE_API_BASE_URL`; never hardcode the URL in components. API keys
must never be placed in frontend environment variables.

### Polling

-   Poll every 2--3 seconds while queued/running.
-   Stop on completed, partial or failed.
-   Avoid duplicate polling loops.
-   Render named stages rather than a fake percentage.

### React Flow

-   Node = file/module; directed edge = import/dependency.
-   Use stable IDs based on repository-relative file path.
-   Highlight cycle members.
-   Clicking a node opens path, finding count, imports/dependants if
    provided.
-   Include Fit View and basic zoom.
-   Provide a textual cycle list and an empty/large-graph state.

### Evidence presentation

Separate "What the analyser observed", "Backend evidence", "Review
risk", and "AI interpretation". Say "not found by the configured scan",
not "does not exist".

## 6. Antigravity Prompts (Gemini 3.8 Flash)

Run prompts sequentially. Ask the agent to inspect the existing
repository before editing, preserve existing working code, and report
actual commands/tests.

**Prompt A --- Scaffold** \> Build the CodeImpact frontend using React,
Vite, TypeScript and Tailwind. Create the app shell, routes, shared
layout and typed interfaces described in this plan. Use Lucide icons, no
emoji icons and no excessive gradients. Do not create backend logic.
Ensure the development server and production build work.

**Prompt B --- Repository and progress** \> Implement the repository
connection form and analysis progress screen. Centralise API calls in
`src/services/api.ts`, use `VITE_API_BASE_URL`, validate GitHub HTTPS
URLs, accept an optional branch, submit to POST
/api/repositories/analyse, and poll GET /api/analyses/{id}. Handle
queued, running, completed, partial and failed states. Keep mock data
behind the same service interface.

**Prompt C --- Overview and findings** \> Implement overview metrics,
findings table, search, filters and finding detail using the exact
shared TypeScript contracts. Keep analyser evidence, risk factors and AI
interpretation visually separate. Support loading, empty, partial and
error states. Do not invent missing values.

**Prompt D --- Graph and AI** \> Implement the dependency graph using
React Flow. Map backend nodes/edges, highlight cycle members, and show
selected-node details. Add an AI explanation panel for summary,
why_it_matters, false_positive_scenarios, verification_steps,
suggested_action and limitations. Do not expose model routing details.

**Prompt E --- Audit** \> Audit the frontend against the agreed API
contract. Find and fix confirmed endpoint/property mismatches,
TypeScript errors, duplicate polling, unhandled states and console
errors. Run the production build and report the exact result.

## 7. Integration Rules

-   Confirm endpoint names and JSON fields with TANUJA_4 before final
    wiring.
-   Use mock data only for UI development; label it as sample data.
-   Do not calculate backend risk scores in the frontend.
-   Do not infer repository matches or test impact.
-   Do not change shared field names independently.
-   Commit in small increments and communicate API changes.

## 8. Test Checklist

-   [ ] Dev server and production build work.
-   [ ] Invalid/empty repository input is handled.
-   [ ] Valid request sends expected JSON.
-   [ ] Polling stops at terminal state.
-   [ ] Overview renders backend metrics.
-   [ ] Search and filters work together.
-   [ ] Finding detail distinguishes evidence from AI.
-   [ ] Graph nodes/edges map correctly and cycles are highlighted.
-   [ ] AI unavailable state does not break the page.
-   [ ] Report download handles errors.
-   [ ] No secrets in frontend bundle.
-   [ ] Primary demo flow has no console errors.

## 9. Handoff

Give TANUJA_4 the consumed endpoints, TypeScript interfaces, required
CORS origin, `VITE_API_BASE_URL`, run/build commands, and remaining API
mismatches.

**Final deliverable:** a working React frontend that completes the
repository-to-results interaction path using real API responses.
