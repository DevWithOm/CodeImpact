"""jscpd execution service for duplicate code detection."""

import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any

try:
    from backend.app.schemas.analysis import ToolCoverageItem
    from backend.app.schemas.finding import Finding
    from backend.app.services.static_analysis.normalizer import normalize_jscpd_findings
    from backend.app.utils.file_utils import is_safe_path, scan_repository_files
    from backend.app.utils.subprocess_runner import redact_secrets, run_command
except ImportError:
    from app.schemas.analysis import ToolCoverageItem
    from app.schemas.finding import Finding
    from app.services.static_analysis.normalizer import normalize_jscpd_findings
    from app.utils.file_utils import is_safe_path, scan_repository_files
    from app.utils.subprocess_runner import redact_secrets, run_command


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


def get_jscpd_version() -> str:
    """Returns the installed jscpd CLI version.

    Returns:
        Version string (e.g. '4.0.5') or 'unknown'.
    """
    jscpd_bin = _find_jscpd_executable()
    res = run_command(["node", jscpd_bin, "--version"], timeout=10)
    if res.succeeded and res.stdout.strip():
        return res.stdout.strip()
    return "unknown"


def run_jscpd(repo_path: str) -> dict[str, Any]:
    """Runs jscpd against a repository workspace and returns structured dictionary.

    Args:
        repo_path: Filesystem path to the target repository workspace.

    Returns:
        Dict with "findings" and "tool_coverage":
        {
            "findings": [...],
            "tool_coverage": {
                "jscpd": {
                    "status": "completed" | "partial" | "failed" | "skipped",
                    "finding_count": int,
                    "message": str | None
                }
            }
        }
    """
    findings, coverage = run_jscpd_analysis(repo_path)
    return {
        "findings": [f.model_dump() for f in findings],
        "tool_coverage": {
            "jscpd": coverage.model_dump(),
        },
    }


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

    # Security check: verify reports directory and reject symlink escape attempts
    codeimpact_dir = repo_path_obj / ".codeimpact"
    reports_dir = Path(output_dir) if output_dir else (codeimpact_dir / "reports" / "jscpd")

    if codeimpact_dir.is_symlink() or reports_dir.is_symlink():
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message="Security violation: .codeimpact directory or report path is an untrusted symbolic link.",
        )

    if not is_safe_path(str(repo_path_obj), str(reports_dir)):
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message="Security violation: report output path escapes the repository workspace.",
        )

    jscpd_bin = _find_jscpd_executable()
    if not Path(jscpd_bin).exists() and not shutil.which(jscpd_bin):
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message="jscpd executable not found in tooling/node_modules. Run npm install in tooling.",
        )

    # Relative reports directory from within repo root
    rel_reports_dir = Path(".codeimpact") / "reports" / "jscpd"
    abs_reports_dir = repo_path_obj / rel_reports_dir
    abs_reports_dir.mkdir(parents=True, exist_ok=True)
    cli_report_file = abs_reports_dir / "jscpd-report.json"

    # Target standard report file location (.codeimpact/reports/jscpd.json)
    standard_report_file = repo_path_obj / ".codeimpact" / "reports" / "jscpd.json"
    standard_report_file.parent.mkdir(parents=True, exist_ok=True)

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

    if result.exit_code != 0 and not cli_report_file.exists():
        error_msg = result.stderr.strip() or result.stdout.strip()
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"jscpd failed with exit code {result.exit_code}: {redact_secrets(error_msg[:300])}",
        )

    # When jscpd finds 0 duplicates, it completes successfully and prints detection time, but creates no report file
    if not cli_report_file.exists():
        if result.exit_code == 0 and "Detection time" in result.stdout:
            empty_report = {
                "duplicates": [],
                "statistics": {
                    "total": {
                        "lines": 0,
                        "tokens": 0,
                        "clones": 0,
                        "duplicatedLines": 0,
                    }
                },
            }
            try:
                standard_report_file.write_text(json.dumps(empty_report, indent=2), encoding="utf-8")
            except OSError:
                pass
            return [], ToolCoverageItem(
                status="completed",
                finding_count=0,
                message=None,
            )
        error_msg = result.stderr.strip() or result.stdout.strip()
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"jscpd report not generated: {redact_secrets(error_msg[:300])}",
        )

    try:
        report_text = cli_report_file.read_text(encoding="utf-8")
        report_data = json.loads(report_text)
        # Persist standard report file at .codeimpact/reports/jscpd.json
        standard_report_file.write_text(report_text, encoding="utf-8")
    except (json.JSONDecodeError, OSError) as exc:
        return [], ToolCoverageItem(
            status="failed",
            finding_count=0,
            message=f"Failed to parse jscpd report JSON: {str(exc)}",
        )

    findings = normalize_jscpd_findings(report_data, repo_root=str(repo_path_obj))

    return findings, ToolCoverageItem(
        status="completed",
        finding_count=len(findings),
        message=None,
    )
