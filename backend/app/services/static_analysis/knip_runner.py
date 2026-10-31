"""Knip execution service for detecting unused files, exports, and dependencies."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from backend.app.schemas.analysis import ToolCoverageItem
from backend.app.schemas.finding import Finding
from backend.app.services.static_analysis.normalizer import normalize_knip_findings
from backend.app.utils.file_utils import scan_repository_files
from backend.app.utils.subprocess_runner import run_command


logger = logging.getLogger(__name__)

KNIP_TIMEOUT_SECONDS = 180


def _find_knip_executable() -> str:
    """Finds the local pinned Knip CLI script."""
    current = Path(__file__).resolve()
    project_root = current.parents[4]
    tooling_knip = project_root / "tooling" / "node_modules" / "knip" / "bin" / "knip.js"
    if tooling_knip.exists():
        return str(tooling_knip)

    workspace_knip = Path("tooling/node_modules/knip/bin/knip.js").resolve()
    if workspace_knip.exists():
        return str(workspace_knip)

    return "knip"


def run_knip_analysis(
    repo_path: str,
    output_dir: str | None = None,
) -> tuple[list[Finding], ToolCoverageItem]:
    """Runs Knip analysis against the specified repository directory.

    Args:
        repo_path: Absolute or relative path to the repository workspace.
        output_dir: Optional directory to store reports. Defaults to repo_path/.codeimpact/reports.

    Returns:
        tuple of (list of normalised findings, ToolCoverageItem)
    """
    repo_path_obj = Path(repo_path).resolve()
    if not repo_path_obj.exists():
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"Target repository path does not exist: {repo_path}",
        )

    # Scan repository first
    scan = scan_repository_files(str(repo_path_obj))
    if scan["eligible_file_count"] == 0:
        return [], ToolCoverageItem(
            status="skipped",
            finding_count=0,
            message="No JavaScript or TypeScript files found to analyze with Knip.",
        )

    knip_bin = _find_knip_executable()
    if knip_bin == "knip" and not Path("tooling/node_modules/knip").exists():
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message="Knip executable not found in tooling/node_modules. Run npm install in tooling.",
        )

    # Prepare reports output directory
    reports_dir = Path(output_dir) if output_dir else (repo_path_obj / ".codeimpact" / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "knip.json"

    # Command runs with cwd=repo_path_obj
    cmd = [
        "node",
        knip_bin,
        "--reporter",
        "json",
        "--no-progress",
        "--no-exit-code",
    ]

    # Resolve node_modules path for Knip dependencies
    tooling_dir = Path(knip_bin).parents[3]
    env = {
        "NODE_PATH": str(tooling_dir / "node_modules"),
    }

    result = run_command(cmd, cwd=str(repo_path_obj), timeout=KNIP_TIMEOUT_SECONDS, env=env)

    if result.timed_out:
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"Knip execution timed out after {KNIP_TIMEOUT_SECONDS}s",
        )

    raw_stdout = result.stdout.strip()

    # Sometimes warnings appear before JSON output; locate JSON boundary
    json_start = raw_stdout.find("{")
    json_end = raw_stdout.rfind("}")

    if json_start == -1 or json_end == -1:
        if result.exit_code != 0:
            error_msg = result.stderr.strip() or raw_stdout
            return [], ToolCoverageItem(
                status="failed",
                finding_count=0,
                message=f"Knip failed with exit code {result.exit_code}: {error_msg[:300]}",
            )
        raw_data = {"files": [], "issues": []}
    else:
        json_str = raw_stdout[json_start : json_end + 1]
        try:
            raw_data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            return [], ToolCoverageItem(
                status="failed",
                finding_count=0,
                message=f"Failed to parse Knip JSON output: {str(exc)}",
            )

    # Save report file for transparency and reporting
    try:
        report_file.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write report to %s: %s", report_file, exc)

    # Normalize findings
    findings = normalize_knip_findings(raw_data, repo_root=str(repo_path_obj))

    status = "completed"
    message = None
    if not scan["has_package_json"]:
        status = "partial"
        message = "Analyzed without root package.json; dependency checks were skipped."

    return findings, ToolCoverageItem(
        status=status,
        finding_count=len(findings),
        message=message,
    )
