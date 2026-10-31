import logging
from typing import Any

from app.adapters.base import DependencyImpactAdapterProtocol

logger = logging.getLogger(__name__)


class DependencyImpactAdapter(DependencyImpactAdapterProtocol):
    """
    Adapter orchestrating SAMAR_3's modular dependency impact pipeline:
    - Phase 2: Madge extraction (single pass per analysis)
    - Phase 3: Directed dependency graph construction
    - Phase 4: Finding-level direct impact analysis
    - Phase 5: Potential test impact mapping
    - Phase 6: Explainable review-risk engine
    """

    def analyze_impact(
        self,
        workspace_path: str,
        findings: list[dict[str, Any]],
        analysis_id: str,
    ) -> dict[str, Any]:
        """Execute single-pass dependency extraction, graph construction, impact, and risk assessment."""
        try:
            from backend.app.services.dependency_impact import (
                analyze_impact,
                analyze_review_risk,
                analyze_test_impact,
                build_dependency_graph,
                run_madge,
            )
        except ImportError:
            from app.services.dependency_impact import (
                analyze_impact,
                analyze_review_risk,
                analyze_test_impact,
                build_dependency_graph,
                run_madge,
            )

        tool_coverage: dict[str, str] = {}

        # 1. Phase 2: Run Madge once
        try:
            madge_result = run_madge(workspace_path)
            dep_map = madge_result.get("dependency_map") or {}
            cycles = madge_result.get("cycles") or []
            madge_status = madge_result.get("status", "success")
            tool_coverage["madge"] = madge_status
        except Exception as exc:
            logger.warning("Madge extraction failed for %s: %s", analysis_id, exc)
            dep_map = {}
            cycles = []
            madge_status = "failed"
            tool_coverage["madge"] = "failed"

        # 2. Phase 3: Build dependency graph once
        try:
            graph_response = build_dependency_graph(
                dependency_map=dep_map,
                cycles=cycles,
                findings=findings,
            )
            if isinstance(graph_response, dict):
                graph = graph_response.get("graph", graph_response)
                graph_status = graph_response.get("status", "success")
            else:
                graph = getattr(graph_response, "graph", graph_response)
                graph_status = getattr(graph_response, "status", "success")
            tool_coverage["dependency_graph"] = graph_status
        except Exception as exc:
            logger.warning("Dependency graph construction failed for %s: %s", analysis_id, exc)
            graph = {"nodes": [], "edges": [], "cycles": [], "stats": {}, "truncated": False}
            graph_status = "failed"
            tool_coverage["dependency_graph"] = "failed"

        # 3. Phase 4: Finding-level direct impact analysis
        try:
            phase4_result = analyze_impact(
                graph=graph,
                findings=findings,
                analysis_id=analysis_id,
            )
            phase4_findings = phase4_result.get("enriched_findings", findings)
            tool_coverage["dependency_impact"] = phase4_result.get("status", "success")
        except Exception as exc:
            logger.warning("Impact analysis failed for %s: %s", analysis_id, exc)
            phase4_findings = findings
            tool_coverage["dependency_impact"] = "failed"

        # 4. Phase 5: Potential test impact mapping
        try:
            phase5_result = analyze_test_impact(
                graph=graph,
                enriched_findings=phase4_findings,
                repo_path=workspace_path,
                analysis_id=analysis_id,
            )
            phase5_findings = phase5_result.get("enriched_findings", phase4_findings)
            entry_points = phase5_result.get("entry_points", [])
            detected_frameworks = phase5_result.get("detected_frameworks", [])
            tool_coverage["test_impact"] = phase5_result.get("status", "success")
        except Exception as exc:
            logger.warning("Test impact mapping failed for %s: %s", analysis_id, exc)
            phase5_findings = phase4_findings
            entry_points = []
            detected_frameworks = []
            tool_coverage["test_impact"] = "failed"

        # 5. Phase 6: Explainable review-risk engine
        try:
            phase6_result = analyze_review_risk(
                graph=graph,
                enriched_findings=phase5_findings,
                entry_points=entry_points,
                analysis_id=analysis_id,
            )
            final_findings = phase6_result.get("enriched_findings", phase5_findings)
            risk_summary = phase6_result.get("summary", {})
            tool_coverage["review_risk"] = phase6_result.get("status", "success")
        except Exception as exc:
            logger.warning("Review risk analysis failed for %s: %s", analysis_id, exc)
            final_findings = phase5_findings
            risk_summary = {}
            tool_coverage["review_risk"] = "failed"

        return {
            "graph": graph,
            "enriched_findings": final_findings,
            "risk_summary": risk_summary,
            "detected_frameworks": detected_frameworks,
            "entry_points": entry_points,
            "tool_coverage": tool_coverage,
        }
