from datetime import datetime, timezone
from typing import Any

from app.schemas.analysis import AnalysisMetrics, AnalysisStatusResponse
from app.schemas.finding import FindingItem
from app.schemas.graph import GraphResponse
from app.services.analysis_store import AnalysisRecord


def format_timestamp(dt: datetime | None) -> str:
    if dt is None:
        return "Not available"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return str(dt)


def generate_markdown_report(
    record: AnalysisRecord | AnalysisStatusResponse,
    findings: list[FindingItem] | None = None,
    graph: GraphResponse | None = None,
    generation_time: datetime | None = None,
) -> str:
    """
    Generates an evidence-based Markdown audit report for a CodeImpact analysis.
    Deterministic service: given identical inputs, produces identical report output.
    """
    gen_time = generation_time or datetime.now(timezone.utc)
    gen_time_str = format_timestamp(gen_time)

    # Extract properties safely from AnalysisRecord or AnalysisStatusResponse
    analysis_id = getattr(record, "analysis_id", "an_unknown")
    repository = getattr(record, "repository", "Unknown Repository")
    repository_url = getattr(record, "repository_url", None) or "Not available"
    branch = getattr(record, "branch", "main")
    commit_sha = getattr(record, "commit_sha", None) or "Not available"

    status_val = getattr(record, "status", "unknown")
    status_str = status_val.value if hasattr(status_val, "value") else str(status_val)

    current_stage = getattr(record, "current_stage", None) or "N/A"
    created_at_str = format_timestamp(getattr(record, "created_at", None))
    completed_at_str = format_timestamp(getattr(record, "completed_at", None))

    metrics: AnalysisMetrics = getattr(record, "metrics", AnalysisMetrics())
    tool_coverage: dict[str, str] = getattr(record, "tool_coverage", {}) or {}
    error_message: str | None = getattr(record, "error_message", None)

    # Findings
    if findings is None:
        findings = getattr(record, "findings", []) or []

    # Graph
    if graph is None:
        graph = getattr(record, "graph", None)

    # Sort findings by review risk priority
    risk_weights = {"higher": 4, "medium": 3, "lower": 2, "unknown": 1}
    sorted_findings = sorted(
        findings,
        key=lambda f: risk_weights.get(getattr(f, "review_risk", "unknown"), 0),
        reverse=True,
    )

    # Build Markdown document
    lines: list[str] = []

    # 1. Header & Title
    lines.append("# CodeImpact Audit Report")
    lines.append("")
    lines.append(f"**Repository:** `{repository}`  ")
    lines.append(f"**Repository URL:** {repository_url}  ")
    lines.append(f"**Analysis ID:** `{analysis_id}`  ")
    lines.append(f"**Report Generated:** {gen_time_str}  ")
    lines.append("**Platform Version:** CodeImpact MVP v1.0  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(
        f"CodeImpact analyzed repository **{repository}** on branch `{branch}`. "
        f"The analysis finished with status **`{status_str.upper()}`** (current stage: `{current_stage}`)."
    )
    lines.append("")
    lines.append(f"- **Total Findings Flagged:** {metrics.total_findings}")
    lines.append(f"  - **Higher Review Risk:** {metrics.higher_risk}")
    lines.append(f"  - **Medium Review Risk:** {metrics.medium_risk}")
    lines.append(f"  - **Lower Review Risk:** {metrics.lower_risk}")
    lines.append(f"  - **Unknown Review Risk:** {metrics.unknown_risk}")
    lines.append(f"- **Circular Dependencies:** {metrics.circular_dependencies} cycles detected")
    lines.append(f"- **Duplicate Code Groups:** {metrics.duplicate_groups} duplication groups identified")
    lines.append(f"- **Mapped Test Candidates:** {metrics.test_candidates} test files identified")
    lines.append("")
    lines.append("> **Important Guidance:**  ")
    lines.append(
        "> Static analysis detects components that lack static references within the configured scan scope. "
        "It does not prove absence of runtime reachability. Never delete code without reviewing dynamic imports, "
        "external API contracts, and running associated tests."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Analysis Metadata
    lines.append("## 2. Analysis Metadata")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("| :--- | :--- |")
    lines.append(f"| **Analysis ID** | `{analysis_id}` |")
    lines.append(f"| **Repository** | `{repository}` |")
    lines.append(f"| **Repository URL** | {repository_url} |")
    lines.append(f"| **Target Branch** | `{branch}` |")
    lines.append(f"| **Commit SHA** | `{commit_sha}` |")
    lines.append(f"| **Job Status** | `{status_str}` |")
    lines.append(f"| **Current Stage** | `{current_stage}` |")
    lines.append(f"| **Started At** | {created_at_str} |")
    lines.append(f"| **Completed At** | {completed_at_str} |")
    lines.append("")

    if error_message:
        lines.append(f"> **Warning / Error Note:** {error_message}")
        lines.append("")

    lines.append("### Tool Coverage")
    lines.append("")
    if tool_coverage:
        lines.append("| Tool / Engine | Status |")
        lines.append("| :--- | :--- |")
        for tool, st in sorted(tool_coverage.items()):
            lines.append(f"| `{tool}` | `{st}` |")
    else:
        lines.append("*No tool coverage metadata recorded.*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4. Summary Metrics Table
    lines.append("## 3. Summary Metrics")
    lines.append("")
    lines.append("| Metric | Count | Description |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| **Total Findings** | {metrics.total_findings} | Total unused, dead, or duplicate code items |")
    lines.append(f"| **Higher Review Risk** | {metrics.higher_risk} | Items with high risk of unexpected breakage if removed |")
    lines.append(f"| **Medium Review Risk** | {metrics.medium_risk} | Standard review candidates requiring inspection |")
    lines.append(f"| **Lower Review Risk** | {metrics.lower_risk} | Candidates with high confidence and isolated usage |")
    lines.append(f"| **Unknown Review Risk** | {metrics.unknown_risk} | Findings with incomplete impact context |")
    lines.append(f"| **Circular Dependencies** | {metrics.circular_dependencies} | Circular dependency cycles detected in module graph |")
    lines.append(f"| **Duplicate Groups** | {metrics.duplicate_groups} | Groups of duplicated code blocks |")
    lines.append(f"| **Test Candidates** | {metrics.test_candidates} | Mapped test suites available for verification |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Detailed Findings Section
    lines.append("## 4. Findings Breakdown & Details")
    lines.append("")
    if not sorted_findings:
        lines.append("*No findings recorded for this analysis.*")
        lines.append("")
    else:
        for idx, f in enumerate(sorted_findings, start=1):
            symbol_txt = f"`{f.symbol}`" if f.symbol else "*None (Module level)*"
            lines_txt = f"{f.start_line}-{f.end_line}" if f.start_line is not None else "Whole file"

            lines.append(f"### 4.{idx}. Finding `{f.finding_id}`: {f.title}")
            lines.append("")
            lines.append(f"- **Category:** `{f.category}`")
            lines.append(f"- **File Path:** `{f.file_path}`")
            lines.append(f"- **Line Range:** `{lines_txt}`")
            lines.append(f"- **Symbol:** {symbol_txt}")
            lines.append(f"- **Review Risk:** **`{f.review_risk.upper()}`**")
            lines.append(f"- **Evidence Class:** `{f.evidence_class}`")
            lines.append(f"- **Source Tool:** `{f.source_tool}`")
            lines.append(f"- **Description:** {f.description}")
            lines.append("")

            # Evidence items
            if f.evidence:
                lines.append("**Evidence Items:**")
                for ev in f.evidence:
                    lines.append(f"- `{ev.kind}` ({ev.status}) via `{ev.source}`: {ev.details}")
                lines.append("")

            # Impact analysis
            if f.impact:
                lines.append("**Dependency & Impact Context:**")
                lines.append(f"- **Direct Dependents Count:** {f.impact.dependency_count}")
                if f.impact.direct_dependants:
                    lines.append(f"- **Direct Importers:** {', '.join(f'`{dep}`' for dep in f.impact.direct_dependants)}")
                lines.append(f"- **Cycle Member:** `{'Yes' if f.impact.cycle_member else 'No'}`")

                if f.impact.related_test_candidates:
                    lines.append("- **Associated Test Candidates:**")
                    for tc in f.impact.related_test_candidates:
                        lines.append(f"  - `{tc.file_path}` ({tc.mapping_strength}): {tc.reason}")

                if f.impact.risk_factors:
                    lines.append("- **Impact Risk Drivers:**")
                    for rf in f.impact.risk_factors:
                        lines.append(f"  - {rf}")
                lines.append("")

            if f.risk_factors and not (f.impact and f.impact.risk_factors):
                lines.append("**Risk Drivers:**")
                for rf in f.risk_factors:
                    lines.append(f"- {rf}")
                lines.append("")

    lines.append("---")
    lines.append("")

    # 6. Dependency Graph & Cycles
    lines.append("## 5. Dependency Graph & Circular Dependencies")
    lines.append("")
    if graph:
        lines.append(f"- **Total Graph Nodes:** {graph.stats.node_count}")
        lines.append(f"- **Total Graph Edges:** {graph.stats.edge_count}")
        lines.append(f"- **Circular Cycles:** {graph.stats.cycle_count}")
        if graph.truncated:
            lines.append("> **Note:** The graph output was truncated due to repository size limits.")
        lines.append("")

        if graph.cycles:
            lines.append("### Detected Circular Dependency Cycles")
            lines.append("")
            for c_idx, cycle in enumerate(graph.cycles, start=1):
                cycle_str = " -> ".join(f"`{node}`" for node in cycle)
                if cycle:
                    cycle_str += f" -> `{cycle[0]}`"
                lines.append(f"{c_idx}. {cycle_str}")
            lines.append("")
        else:
            lines.append("*No circular dependency cycles detected.*")
            lines.append("")
    else:
        lines.append("*Dependency graph data was not available for this analysis.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 7. Verification Guidelines & Limitations
    lines.append("## 6. Pre-Cleanup Verification Guidelines & Limitations")
    lines.append("")
    lines.append("### Pre-Cleanup Developer Checklist")
    lines.append("Before removing any code flagged in this audit, verify the following:")
    lines.append("- [ ] **Dynamic Invocations:** Search the repository for dynamic imports (`import(...)`), string-based lookups, or reflection that reference the symbol or file.")
    lines.append("- [ ] **Public API Surface:** Check if the flagged export or file is part of a package entry point (`index.ts`, `main` in `package.json`) consumed by external consumers.")
    lines.append("- [ ] **Test Execution:** Execute all associated test candidates identified in Section 4.")
    lines.append("- [ ] **Framework Conventions:** Ensure the file is not a framework-specific convention file (e.g., Next.js pages, Vite plugin hooks, test setup scripts).")
    lines.append("- [ ] **Peer Review:** Share findings with author or team before refactoring.")
    lines.append("")
    lines.append("### Analysis Limitations")
    lines.append("- Static analysis tools observe only static references within the scanned workspace.")
    lines.append("- Runtime reachability and dynamic execution cannot be verified statically.")
    lines.append("- Partial tool execution or unsupported file types may result in incomplete coverage.")
    lines.append("")
    lines.append("---")
    lines.append("*Generated automatically by CodeImpact.*")
    lines.append("")

    return "\n".join(lines)
