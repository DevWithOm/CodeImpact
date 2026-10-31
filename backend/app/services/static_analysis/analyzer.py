"""Unified static code analysis engine for CodeImpact.

Coordinates Knip and jscpd execution, aggregate findings, and tool coverage reporting.
"""

import logging
from pathlib import Path
from typing import Any

from backend.app.schemas.analysis import AnalysisResult, ToolCoverageItem
from backend.app.services.static_analysis.jscpd_runner import run_jscpd_analysis
from backend.app.services.static_analysis.knip_runner import run_knip_analysis


logger = logging.getLogger(__name__)


def analyze_repository(
    repo_path: str,
    analysis_id: str,
) -> dict[str, Any]:
    """Runs all configured static code analysis tools on a retrieved repository.

    Args:
        repo_path: Local filesystem path to repository workspace.
        analysis_id: Unique analysis identifier.

    Returns:
        Dict adhering strictly to the shared analysis contract:
        {
            "findings": [ ... ],
            "tool_coverage": {
                "knip": {
                    "status": "completed" | "partial" | "failed" | "skipped",
                    "finding_count": int,
                    "message": str | None
                },
                "jscpd": {
                    "status": "completed" | "partial" | "failed" | "skipped",
                    "finding_count": int,
                    "message": str | None
                }
            }
        }
    """
    repo_path_obj = Path(repo_path).resolve()
    reports_dir = repo_path_obj / ".codeimpact" / "reports"
    try:
        if not (repo_path_obj / ".codeimpact").is_symlink():
            reports_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    all_findings = []

    # 1. Knip Analysis
    try:
        knip_findings, knip_coverage = run_knip_analysis(
            repo_path=str(repo_path_obj),
            output_dir=str(reports_dir),
        )
        all_findings.extend(knip_findings)
    except Exception as exc:
        logger.exception("Unexpected error executing Knip: %s", exc)
        knip_coverage = ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"Knip execution error: {str(exc)}",
        )

    # 2. jscpd Analysis
    try:
        jscpd_findings, jscpd_coverage = run_jscpd_analysis(
            repo_path=str(repo_path_obj),
            output_dir=str(reports_dir / "jscpd"),
        )
        all_findings.extend(jscpd_findings)
    except Exception as exc:
        logger.exception("Unexpected error executing jscpd: %s", exc)
        jscpd_coverage = ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"jscpd execution error: {str(exc)}",
        )

    # Convert Pydantic findings and coverage to dictionaries
    serializable_findings = [f.model_dump() for f in all_findings]
    coverage_dict = {
        "knip": knip_coverage.model_dump(),
        "jscpd": jscpd_coverage.model_dump(),
    }

    return {
        "findings": serializable_findings,
        "tool_coverage": coverage_dict,
    }

