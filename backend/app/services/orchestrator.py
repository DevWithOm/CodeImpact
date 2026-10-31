from __future__ import annotations

import asyncio
import logging
from typing import Any
import uuid

try:
    from app.adapters.base import (
        DependencyImpactAdapterProtocol,
        RepositoryAdapterProtocol,
        StaticAnalysisAdapterProtocol,
    )
    from app.adapters.dependency_impact_adapter import DependencyImpactAdapter
    from app.adapters.repository_adapter import RepositoryAdapter
    from app.adapters.static_analysis_adapter import StaticAnalysisAdapter
    from app.schemas.analysis import AnalysisRequest, AnalysisStatus
    from app.schemas.evidence import EvidenceItem, FindingImpact, TestCandidate
    from app.schemas.finding import FindingItem
    from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStats
    from app.services.analysis_store import AnalysisStore, analysis_store as default_store
except ImportError:
    from backend.app.adapters.base import (
        DependencyImpactAdapterProtocol,
        RepositoryAdapterProtocol,
        StaticAnalysisAdapterProtocol,
    )
    from backend.app.adapters.dependency_impact_adapter import DependencyImpactAdapter
    from backend.app.adapters.repository_adapter import RepositoryAdapter
    from backend.app.adapters.static_analysis_adapter import StaticAnalysisAdapter
    from backend.app.schemas.analysis import AnalysisRequest, AnalysisStatus
    from backend.app.schemas.evidence import EvidenceItem, FindingImpact, TestCandidate
    from backend.app.schemas.finding import FindingItem
    from backend.app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStats
    from backend.app.services.analysis_store import AnalysisStore, analysis_store as default_store

logger = logging.getLogger(__name__)


def normalize_finding_dict(item: dict[str, Any]) -> FindingItem:
    """Normalize finding dictionaries from static analysis and dependency impact engines into FindingItem."""
    evidence_list = []
    for ev in item.get("evidence", []):
        if isinstance(ev, dict):
            evidence_list.append(EvidenceItem(**ev))
        elif isinstance(ev, EvidenceItem):
            evidence_list.append(ev)

    impact_obj = None
    raw_impact = item.get("impact")
    if isinstance(raw_impact, dict):
        test_candidates = []
        for tc in raw_impact.get("related_test_candidates", []):
            if isinstance(tc, dict):
                test_candidates.append(TestCandidate(**tc))
            elif isinstance(tc, TestCandidate):
                test_candidates.append(tc)

        impact_obj = FindingImpact(
            direct_dependants=raw_impact.get("direct_dependants", []),
            dependency_count=raw_impact.get("dependency_count", 0),
            cycle_member=raw_impact.get("cycle_member", False),
            related_test_candidates=test_candidates,
            risk_factors=raw_impact.get("risk_factors", []),
            review_risk=raw_impact.get("review_risk", "unknown"),
        )
    elif isinstance(raw_impact, FindingImpact):
        impact_obj = raw_impact
    elif "direct_dependants" in item or "test_impact" in item:
        # Synthesize FindingImpact from SAMAR_3 enriched finding
        raw_direct = [
            d.get("file_path", "") if isinstance(d, dict) else str(d)
            for d in item.get("direct_dependants", [])
        ]
        raw_direct = [p for p in raw_direct if p]
        test_impact_data = item.get("test_impact") or {}
        raw_candidates = test_impact_data.get("candidate_tests", [])
        test_candidates = [
            TestCandidate(
                file_path=c.get("file_path", "") if isinstance(c, dict) else getattr(c, "file_path", ""),
                reason=c.get("reason", "Potential test relationship") if isinstance(c, dict) else getattr(c, "reason", ""),
                mapping_strength=c.get("mapping_status", "direct") if isinstance(c, dict) else getattr(c, "mapping_status", "direct"),
            )
            for c in raw_candidates if (isinstance(c, dict) or hasattr(c, "file_path"))
        ]
        impact_obj = FindingImpact(
            direct_dependants=raw_direct,
            dependency_count=len(raw_direct),
            cycle_member=bool(item.get("cycle_member", False)),
            related_test_candidates=test_candidates,
            risk_factors=item.get("risk_factors", []),
            review_risk=str(item.get("review_risk", "unknown")),
        )

    raw_category = item.get("category", "unknown")
    if hasattr(raw_category, "value"):
        category_str = str(raw_category.value)
    else:
        category_str = str(raw_category)
        if category_str.startswith("FindingCategory."):
            category_str = category_str.split(".", 1)[1].lower()

    raw_ev_class = item.get("evidence_class", "inconclusive")
    if hasattr(raw_ev_class, "value"):
        evidence_class_str = str(raw_ev_class.value)
    else:
        evidence_class_str = str(raw_ev_class)
        if evidence_class_str.startswith("EvidenceClass."):
            evidence_class_str = evidence_class_str.split(".", 1)[1].lower()

    raw_risk = item.get("review_risk", "unknown")
    if hasattr(raw_risk, "value"):
        risk_str = str(raw_risk.value)
    else:
        risk_str = str(raw_risk)
        if risk_str.startswith("ReviewRisk."):
            risk_str = risk_str.split(".", 1)[1].lower()

    finding_item = FindingItem(
        finding_id=str(item.get("finding_id", "f_unknown")),
        category=category_str,
        title=str(item.get("title", "Finding")),
        file_path=str(item.get("file_path", "")),
        start_line=item.get("start_line"),
        end_line=item.get("end_line"),
        symbol=item.get("symbol"),
        source_tool=str(item.get("source_tool", "analyzer")),
        description=str(item.get("description", "")),
        evidence_class=evidence_class_str,
        review_risk=risk_str,
        evidence=evidence_list,
        risk_factors=item.get("risk_factors", []),
        impact=impact_obj,
    )

    # Preserve SAMAR_3 review-risk and impact attributes on the model
    for k in (
        "risk_score",
        "risk_confidence",
        "risk_assessment",
        "test_impact",
        "direct_dependants",
        "direct_dependencies",
        "cycle_member",
        "cycles",
        "module_type",
        "is_entry_point",
        "is_leaf",
        "limitations",
    ):
        if k in item:
            try:
                setattr(finding_item, k, item[k])
            except Exception:
                pass

    return finding_item


def normalize_graph_dict(analysis_id: str, raw_graph: Any) -> GraphResponse:
    """Normalize dependency graph from dependency impact engine into GraphResponse schema."""
    if isinstance(raw_graph, GraphResponse):
        return raw_graph

    if not isinstance(raw_graph, dict):
        return GraphResponse(
            analysis_id=analysis_id,
            nodes=[],
            edges=[],
            cycles=[],
            stats=GraphStats(node_count=0, edge_count=0, cycle_count=0),
            truncated=False,
        )

    nodes: list[GraphNode] = []
    for n in raw_graph.get("nodes", []):
        if isinstance(n, GraphNode):
            nodes.append(n)
        elif isinstance(n, dict):
            nodes.append(
                GraphNode(
                    id=str(n.get("id", "")),
                    label=str(n.get("label", n.get("id", ""))),
                    file_path=str(n.get("file_path", n.get("id", ""))),
                    incoming_count=int(n.get("incoming_count", 0)),
                    outgoing_count=int(n.get("outgoing_count", 0)),
                    in_cycle=bool(n.get("in_cycle", False)),
                    is_entry_point=bool(n.get("is_entry_point", False)),
                    review_risk=str(n.get("review_risk", "unknown")),
                )
            )

    edges: list[GraphEdge] = []
    for e in raw_graph.get("edges", []):
        if isinstance(e, GraphEdge):
            edges.append(e)
        elif isinstance(e, dict):
            s = str(e.get("source", ""))
            t = str(e.get("target", ""))
            eid = str(e.get("id") or (f"{s}->{t}" if s and t else ""))
            edges.append(
                GraphEdge(
                    id=eid,
                    source=s,
                    target=t,
                    in_cycle=bool(e.get("in_cycle", False)),
                    cycle_ids=e.get("cycle_ids", []),
                )
            )

    cycles = list(raw_graph.get("cycles", []))
    raw_stats = raw_graph.get("stats", {})
    stats = GraphStats(
        node_count=raw_stats.get("node_count", len(nodes)),
        edge_count=raw_stats.get("edge_count", len(edges)),
        cycle_count=raw_stats.get("cycle_count", len(cycles)),
    )

    return GraphResponse(
        analysis_id=analysis_id,
        nodes=nodes,
        edges=edges,
        cycles=cycles,
        stats=stats,
        truncated=bool(raw_graph.get("truncated", False)),
    )


class AnalysisOrchestrator:
    """Coordinates repository retrieval, static code analysis, and dependency impact analysis."""

    def __init__(
        self,
        store: AnalysisStore | None = None,
        repo_adapter: RepositoryAdapterProtocol | None = None,
        static_adapter: StaticAnalysisAdapterProtocol | None = None,
        dependency_adapter: DependencyImpactAdapterProtocol | None = None,
    ) -> None:
        self.store = store or default_store
        self.repo_adapter = repo_adapter or RepositoryAdapter()
        self.static_adapter = static_adapter or StaticAnalysisAdapter()
        self.dependency_adapter = dependency_adapter or DependencyImpactAdapter()

    async def run_analysis(self, request: AnalysisRequest) -> dict[str, Any]:
        """Programmatic end-to-end execution of the full analysis pipeline."""
        analysis_id = f"an_{uuid.uuid4().hex[:8]}"
        self.store.create_analysis(analysis_id=analysis_id, request=request)
        await self.run_pipeline(analysis_id)
        record = self.store.get_record(analysis_id)
        if record is None:
            return {"analysis_id": analysis_id, "status": "failed", "error": "Analysis record missing"}

        return {
            "analysis_id": analysis_id,
            "status": record.status.value if hasattr(record.status, "value") else str(record.status),
            "repository": record.to_status_response().model_dump(),
            "findings": [f.model_dump() for f in record.findings],
            "graph": record.graph.model_dump() if record.graph else None,
            "metrics": record.metrics.model_dump(),
            "tool_coverage": record.tool_coverage,
        }

    async def run_pipeline(self, analysis_id: str) -> None:
        """Executes the analysis pipeline in the background."""
        record = self.store.get_record(analysis_id)
        if record is None:
            status_resp = self.store.get_analysis(analysis_id)
            if status_resp is None:
                logger.error("Cannot run pipeline: analysis %s not found in store", analysis_id)
                return
            repo_id = status_resp.repository
            repo_url = repo_id if repo_id.startswith(("http://", "https://")) else f"https://github.com/{repo_id}"
            branch = status_resp.branch
        else:
            repo_id = record.repository
            repo_url = record.repository_url or (repo_id if repo_id.startswith(("http://", "https://")) else f"https://github.com/{repo_id}")
            branch = record.branch

        logger.info("Starting analysis pipeline for %s (%s)", analysis_id, repo_id)
        self.store.update_status(analysis_id, AnalysisStatus.RUNNING, stage="cloning")

        workspace_path = None
        commit_sha = None
        tool_coverage: dict[str, str] = {}
        findings: list[FindingItem] = []
        graph: GraphResponse = GraphResponse(
            analysis_id=analysis_id,
            nodes=[],
            edges=[],
            cycles=[],
            stats=GraphStats(node_count=0, edge_count=0, cycle_count=0),
            truncated=False,
        )

        try:
            # Stage 1: Repository Retrieval & Workspace Setup
            self.store.update_status(analysis_id, AnalysisStatus.RUNNING, stage="cloning")
            try:
                retrieval_res = await asyncio.to_thread(
                    self.repo_adapter.retrieve_repository,
                    repository_url=repo_url,
                    branch=branch,
                    analysis_id=analysis_id,
                )
                workspace_path = retrieval_res["workspace_path"]
                commit_sha = retrieval_res.get("commit_sha")
                tool_coverage["git"] = "success"
                logger.info("Retrieved repository %s to workspace %s", repo_id, workspace_path)
            except Exception as exc:
                logger.exception("Repository retrieval failed for %s: %s", analysis_id, exc)
                tool_coverage["git"] = "failed"
                self.store.update_status(
                    analysis_id=analysis_id,
                    status=AnalysisStatus.FAILED,
                    stage="failed",
                    error_message=f"Repository retrieval failed: {exc}",
                )
                return

            # Stage 2: Static Code Analysis (Knip, jscpd)
            self.store.update_status(analysis_id, AnalysisStatus.RUNNING, stage="static_analysis")
            raw_findings = []
            try:
                static_res = await asyncio.to_thread(
                    self.static_adapter.analyze_repository,
                    workspace_path,
                    analysis_id,
                )
                raw_findings = static_res.get("findings", [])
                tool_coverage.update(static_res.get("tool_coverage", {}))
            except Exception as exc:
                logger.warning("Static code analysis failed for %s: %s", analysis_id, exc)
                tool_coverage["static_analysis"] = "failed"

            # Stage 3: Dependency Graph Construction & Impact Analysis (Madge)
            self.store.update_status(analysis_id, AnalysisStatus.RUNNING, stage="dependency_analysis")
            raw_graph = {}
            try:
                impact_res = await asyncio.to_thread(
                    self.dependency_adapter.analyze_impact,
                    workspace_path,
                    raw_findings,
                    analysis_id,
                )
                raw_graph = impact_res.get("graph", {})
                raw_findings = impact_res.get("enriched_findings", raw_findings)
                tool_coverage.update(impact_res.get("tool_coverage", {"dependency_impact": "success"}))
            except Exception as exc:
                logger.warning("Dependency impact analysis failed for %s: %s", analysis_id, exc)
                tool_coverage["dependency_impact"] = "failed"

            # Stage 4: Risk Scoring & Result Assembly
            self.store.update_status(analysis_id, AnalysisStatus.RUNNING, stage="result_assembly")
            findings = [normalize_finding_dict(f) for f in raw_findings]
            graph = normalize_graph_dict(analysis_id, raw_graph)

            # Determine final status
            failed_tools = [tool for tool, status in tool_coverage.items() if status == "failed"]
            if failed_tools:
                if len(findings) > 0 or len(graph.nodes) > 0:
                    final_status = AnalysisStatus.PARTIAL
                else:
                    final_status = AnalysisStatus.FAILED
            else:
                final_status = AnalysisStatus.COMPLETED

            error_msg = f"Tools failed: {', '.join(failed_tools)}" if failed_tools else None

            self.store.update_results(
                analysis_id=analysis_id,
                findings=findings,
                graph=graph,
                tool_coverage=tool_coverage,
                commit_sha=commit_sha,
                status=final_status,
                error_message=error_msg,
            )
            logger.info("Analysis %s completed with status %s", analysis_id, final_status.value)

        except Exception as exc:
            logger.exception("Unexpected error in analysis pipeline for %s: %s", analysis_id, exc)
            self.store.update_status(
                analysis_id=analysis_id,
                status=AnalysisStatus.FAILED,
                stage="failed",
                error_message=f"Pipeline error: {exc}",
            )
        finally:
            if workspace_path:
                await asyncio.to_thread(self.repo_adapter.cleanup_workspace, workspace_path)


# Default orchestrator singleton
orchestrator = AnalysisOrchestrator()
