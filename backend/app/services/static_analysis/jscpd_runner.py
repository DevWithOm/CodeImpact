"""jscpd execution service for duplicate code detection."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from backend.app.schemas.analysis import ToolCoverageItem
from backend.app.schemas.finding import Finding
from backend.app.services.static_analysis.normalizer import normalize_jscpd_findings
from backend.app.utils.file_utils import scan_repository_files
from backend.app.utils.subprocess_runner import run_command


logger = logging.getLogger(__name__)

JSCPD_TIMEOUT_SECONDS = 180


def _find_jscpd_executable() -> str:
    """Finds the local pinned jscpd CLI script."""
    current = Path(__file__).resolve()
    project_root = current.parents[4]
    tooling_jscpd = project_root / "tooling" / "node_modules" / "jscpd" / "bin" / "jscpd"
    if tooling_jscpd.exists():
        return str(tooling_jscpd)

    workspace_jscpd = Path("tooling/node_modules/jscpd/bin/jscpd").resolve()
    if workspace_jscpd.exists():
        return str(workspace_jscpd)

    return "jscpd"


def run_jscpd_analysis(
    repo_path: str,
    output_dir: str | None = None,
) -> tuple[list[Finding], ToolCoverageItem]:
    """Runs jscpd duplicate code analysis against the specified repository directory.

    Args:
        repo_path: Absolute or relative path to the repository workspace.
        output_dir: Optional directory to store reports. Defaults to repo_path/.codeimpact/reports/jscpd.

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

    scan = scan_repository_files(str(repo_path_obj))
    if scan["eligible_file_count"] == 0:
        return [], ToolCoverageItem(
            status="skipped",
            finding_count=0,
            message="No JavaScript or TypeScript files found to analyze with jscpd.",
        )

    jscpd_bin = _find_jscpd_executable()
    if jscpd_bin == "jscpd" and not Path("tooling/node_modules/jscpd").exists():
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message="jscpd executable not found in tooling/node_modules. Run npm install in tooling.",
        )

    # Relative reports directory from within repo root
    rel_reports_dir = Path(".codeimpact") / "reports" / "jscpd"
    abs_reports_dir = repo_path_obj / rel_reports_dir
    abs_reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = abs_reports_dir / "jscpd-report.json"

    cmd = [
        "node",
        jscpd_bin,
        ".",
        "-r",
        "json",
        "-o",
        str(rel_reports_dir.as_posix()),
        "--exitCode",
        "0",
        "--ignore",
        "**/.codeimpact/**,**/dist/**,**/build/**,**/node_modules/**,**/.git/**,**/.next/**,**/coverage/**",
    ]

    tooling_dir = Path(jscpd_bin).parents[3]
    env = {
        "NODE_PATH": str(tooling_dir / "node_modules"),
    }

    result = run_command(cmd, cwd=str(repo_path_obj), timeout=JSCPD_TIMEOUT_SECONDS, env=env)

    if result.timed_out:
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"jscpd execution timed out after {JSCPD_TIMEOUT_SECONDS}s",
        )

    if not report_file.exists():
        error_msg = result.stderr.strip() or result.stdout.strip()
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"jscpd report not generated: {error_msg[:300]}",
        )

    try:
        report_data = json.loads(report_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"Failed to parse jscpd-report.json: {str(exc)}",
        )

    findings = normalize_jscpd_findings(report_data, repo_root=str(repo_path_obj))

    return findings, ToolCoverageItem(
        status="completed",
        finding_count=len(findings),
        message=None,
    )
