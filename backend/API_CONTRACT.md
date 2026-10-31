# CodeImpact — Shared API Contract (v1.0 MVP)

**Target Version:** 1.0 (Hackathon MVP)  
**Authors / Stakeholders:** TANUJA_4 (Backend/AI/Lead), BHOOMI_1 (Frontend), OM_2 (Static Analysis), SAMAR_3 (Dependency/Impact)  
**Design Standard:** RESTful JSON, asynchronous job orchestration, snake_case attributes.

---

## 1. Global Conventions & Standards

- **Base URL:** `/` (Local: `http://localhost:8000`)
- **Data Format:** JSON for requests and responses (except `/report` which returns `text/markdown`).
- **Naming Convention:** `snake_case` for all JSON keys.
- **Timestamp Format:** ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- **Job Flow:** Analysis is asynchronous. POST returns `202 Accepted` with an `analysis_id`. Frontend polls `GET /api/analyses/{analysis_id}`.
- **Allowed Job Statuses:**
  - `queued`: Request validated, job created in queue.
  - `running`: Retrieval, static analysis, or dependency mapping in progress.
  - `completed`: All stages completed successfully.
  - `partial`: At least one required output generated, but one non-critical tool failed (e.g., Knip ran but jscpd or Madge failed).
  - `failed`: Fatal error preventing analysis (e.g. invalid repo URL, unreachable host, not a supported JS/TS repository).

### Standard Error Response Envelope
HTTP status `400`, `404`, `422`, `500`:
```json
{
  "error": {
    "code": "REPOSITORY_NOT_ACCESSIBLE",
    "message": "The repository could not be accessed. Check that it is public and the URL is correct.",
    "request_id": "req_abc123"
  }
}
```

Common Error Codes:
- `INVALID_REPOSITORY_URL`: URL is malformed or not a supported GitHub URL.
- `REPOSITORY_NOT_ACCESSIBLE`: Repository not found or inaccessible (private/non-existent).
- `UNSUPPORTED_PROJECT_TYPE`: No JavaScript or TypeScript project detected.
- `ANALYSIS_NOT_FOUND`: Specified `analysis_id` does not exist.
- `FINDING_NOT_FOUND`: Specified `finding_id` not found in analysis.
- `AI_SERVICE_UNAVAILABLE`: Explanation service currently unavailable (fallback message returned).

---

## 2. API Endpoints

### 2.1 Health Check

- **Endpoint:** `GET /health`
- **Purpose:** Fast liveness probe for frontend and dev environment.
- **HTTP Status:** `200 OK`
- **Response Schema:**
```json
{
  "status": "ok"
}
```

---

### 2.2 Start Repository Analysis

- **Endpoint:** `POST /api/repositories/analyse`
- **Purpose:** Initiates asynchronous clone and analysis pipeline. Returns immediately.
- **HTTP Status:** `202 Accepted`
- **Request Schema:**
```json
{
  "repository_url": "https://github.com/owner/repository",
  "branch": "main"
}
```
*(Note: `branch` is optional; defaults to repo default branch if omitted or null).*

- **Response Schema:**
```json
{
  "analysis_id": "an_demo123",
  "status": "queued",
  "repository": "owner/repository",
  "branch": "main"
}
```

---

### 2.3 Analysis Status & Summary Metrics

- **Endpoint:** `GET /api/analyses/{analysis_id}`
- **Purpose:** Polling endpoint for progress and high-level dashboard metrics.
- **HTTP Status:** `200 OK`
- **Response Schema:**
```json
{
  "analysis_id": "an_demo123",
  "repository": "owner/repository",
  "branch": "main",
  "commit_sha": "a1b2c3d4",
  "status": "completed",
  "current_stage": "completed",
  "created_at": "2026-10-31T10:00:00Z",
  "completed_at": "2026-10-31T10:00:18Z",
  "metrics": {
    "total_findings": 12,
    "higher_risk": 2,
    "medium_risk": 5,
    "lower_risk": 3,
    "unknown_risk": 2,
    "circular_dependencies": 1,
    "duplicate_groups": 2,
    "test_candidates": 4
  },
  "tool_coverage": {
    "knip": "success",
    "jscpd": "success",
    "madge": "success"
  }
}
```
*`current_stage` values:* `queued`, `cloning`, `static_analysis`, `dependency_graph`, `risk_scoring`, `completed`, `failed`.

---

### 2.4 Findings Explorer (List & Filters)

- **Endpoint:** `GET /api/analyses/{analysis_id}/findings`
- **Purpose:** Paginated, filterable list of detected dead code and duplication findings.
- **HTTP Status:** `200 OK`
- **Query Parameters:**
  - `category` (optional string): e.g., `unused_file`, `unused_export`, `unused_dependency`, `duplicate_block`
  - `review_risk` (optional string): `higher`, `medium`, `lower`, `unknown`
  - `evidence_class` (optional string): `strong`, `inconclusive`, `contradictory`
  - `source_tool` (optional string): `knip`, `jscpd`
  - `path` (optional string): File path prefix or substring filter
  - `search` (optional string): Free-text search on symbol, file path, description
  - `sort` (optional string): `risk_desc`, `risk_asc`, `path_asc` (default: `risk_desc`)
  - `page` (optional int, default: `1`)
  - `page_size` (optional int, default: `50`, max: `100`)
- **Response Schema:**
```json
{
  "analysis_id": "an_demo123",
  "items": [
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
          "details": "No direct static reference was returned.",
          "value": null
        }
      ],
      "risk_factors": [
        "Symbol exported from shared module",
        "Dynamic import not ruled out"
      ],
      "impact": {
        "direct_dependants": ["src/app.ts"],
        "dependency_count": 1,
        "cycle_member": false
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "tool_coverage": {
    "knip": "success",
    "jscpd": "success"
  }
}
```

---

### 2.5 Finding Detail

- **Endpoint:** `GET /api/analyses/{analysis_id}/findings/{finding_id}`
- **Purpose:** Full detail view for a single finding with comprehensive evidence and test mappings.
- **HTTP Status:** `200 OK`
- **Response Schema:**
```json
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
  "risk_factors": [
    "Exported from utility module",
    "May be dynamically resolved"
  ],
  "impact": {
    "direct_dependants": ["src/app.ts"],
    "dependency_count": 1,
    "cycle_member": false,
    "related_test_candidates": [
      {
        "file_path": "tests/helpers.test.ts",
        "reason": "Direct test suite for module",
        "mapping_strength": "direct"
      }
    ]
  },
  "limitations": [
    "Static analysis cannot prove runtime reachability."
  ]
}
```

---

### 2.6 Dependency Graph

- **Endpoint:** `GET /api/analyses/{analysis_id}/graph`
- **Purpose:** Directed dependency graph and detected circular dependency cycles for visualization (React Flow).
- **Direction:** `source` imports `target` (`source -> target`).
- **HTTP Status:** `200 OK`
- **Response Schema:**
```json
{
  "analysis_id": "an_demo123",
  "nodes": [
    {
      "id": "src/main.ts",
      "label": "main.ts",
      "file_path": "src/main.ts",
      "finding_count": 1,
      "cycle_member": false
    },
    {
      "id": "src/app.ts",
      "label": "app.ts",
      "file_path": "src/app.ts",
      "finding_count": 0,
      "cycle_member": false
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
  "cycles": [
    ["src/a.ts", "src/b.ts"]
  ],
  "stats": {
    "node_count": 2,
    "edge_count": 1,
    "cycle_count": 1
  },
  "truncated": false
}
```

---

### 2.7 AI Explanation & Recommendation

- **Endpoint:** `POST /api/analyses/{analysis_id}/explain`
- **Purpose:** On-demand AI explanation grounded strictly in the finding's evidence, risk, and impact data.
- **HTTP Status:** `200 OK`
- **Request Schema:**
```json
{
  "finding_id": "f_001"
}
```
- **Response Schema:**
```json
{
  "summary": "No static reference was found by the configured scan.",
  "why_it_matters": "The export may represent unnecessary maintenance surface.",
  "false_positive_scenarios": [
    "The symbol may be loaded dynamically via string reflection or plug-in system."
  ],
  "verification_steps": [
    "Check runtime registration and dynamic imports before removing.",
    "Run tests/helpers.test.ts to verify dependent suites."
  ],
  "suggested_action": "Review before making a change.",
  "limitations": [
    "Static analysis cannot prove runtime reachability."
  ]
}
```
*Design Rule:* Provider-neutral. Does not expose model name or raw prompts.

---

### 2.8 Markdown Report Download

- **Endpoint:** `GET /api/analyses/{analysis_id}/report`
- **Purpose:** Generate and download a comprehensive Markdown audit report.
- **HTTP Status:** `200 OK`
- **Response Header:**
  - `Content-Type: text/markdown; charset=utf-8`
  - `Content-Disposition: attachment; filename="CodeImpact_Report_owner_repo_{analysis_id}.md"`
- **Response Body:** Full Markdown string containing repository overview, metrics, top risks, findings breakdown, cycles, and AI notes.
