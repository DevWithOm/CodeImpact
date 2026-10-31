"""Comprehensive Security and Robustness Verification Test Suite for CodeImpact.

Validates:
1. URL validation & credential rejection
2. Control character rejection
3. Non-HTTPS scheme rejection
4. Branch argument / flag injection rejection
5. Branch command separator rejection
6. Secret redaction (GitHub PATs)
7. Secret redaction (Bearer tokens)
8. Secret redaction (Passwords in URLs)
9. Symlinked report path rejection
10. Report path outside workspace rejection
11. Corrupt/empty jscpd report handling
12. Missing jscpd binary handling
13. Subprocess output truncation for oversized outputs (>5MB)
14. Workspace cleanup on clone failure
15. Orchestration isolation: Knip failure does not mask jscpd
16. Orchestration isolation: jscpd failure does not mask Knip
17. jscpd token count 0 not coerced to null
18. Knip executable config (knip.js / knip.ts) security trust boundary
"""

import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import pytest

from backend.app.schemas.analysis import ToolCoverageItem
from backend.app.schemas.evidence import EvidenceItem
from backend.app.schemas.finding import Finding
from backend.app.services.repository.github_service import (
    RepositoryRetrievalError,
    retrieve_repository,
    validate_branch_name,
    validate_github_url,
)
from backend.app.services.static_analysis.analyzer import analyze_repository
from backend.app.services.static_analysis.jscpd_runner import run_jscpd_analysis
from backend.app.services.static_analysis.knip_runner import run_knip_analysis
from backend.app.services.static_analysis.normalizer import normalize_jscpd_findings
from backend.app.utils.subprocess_runner import (
    CommandResult,
    _truncate_output,
    redact_secrets,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_js_repo(tmp_path: Path) -> Path:
    """Creates a minimal valid JS/TS repository in a temporary directory."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    pkg_json = {
        "name": "sample-repo",
        "version": "1.0.0",
        "main": "src/index.js",
    }
    (repo_dir / "package.json").write_text(json.dumps(pkg_json), encoding="utf-8")

    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "index.js").write_text("console.log('hello');\n", encoding="utf-8")

    return repo_dir


# ---------------------------------------------------------------------------
# 1. URL Validation: Embedded Credentials Rejection
# ---------------------------------------------------------------------------

def test_rejects_embedded_credentials_in_url():
    """Embedded credentials in repository URLs must be strictly rejected."""
    with pytest.raises((ValueError, RepositoryRetrievalError), match="Embedded credentials"):
        validate_github_url("https://user:password@github.com/owner/repo.git")

    with pytest.raises((ValueError, RepositoryRetrievalError), match="Embedded credentials"):
        validate_github_url("https://ghp_1234567890abcdef@github.com/owner/repo")

    with pytest.raises((ValueError, RepositoryRetrievalError)):
        retrieve_repository("https://user:password@github.com/owner/repo.git")


# ---------------------------------------------------------------------------
# 2. URL Validation: Control Character Rejection
# ---------------------------------------------------------------------------

def test_rejects_control_characters_in_url():
    """URLs containing control characters or whitespace must be rejected."""
    invalid_urls = [
        "https://github.com/owner/repo\n.git",
        "https://github.com/owner/repo\r\n",
        "https://github.com/owner/repo\0.git",
        "https://github.com/owner/repo\tfoo",
        "https://github.com/owner/ repo.git",
    ]
    for url in invalid_urls:
        with pytest.raises((ValueError, RepositoryRetrievalError)):
            validate_github_url(url)


# ---------------------------------------------------------------------------
# 3. URL Validation: Non-HTTPS Schemes Rejection
# ---------------------------------------------------------------------------

def test_rejects_non_https_git_schemes():
    """Only HTTPS URLs on github.com are permitted; others must be rejected."""
    non_https_urls = [
        "http://github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
        "ssh://git@github.com/owner/repo.git",
        "file:///tmp/malicious/repo",
        "ftp://github.com/owner/repo.git",
        "https://gitlab.com/owner/repo.git",
        "https://bitbucket.org/owner/repo.git",
    ]
    for url in non_https_urls:
        with pytest.raises((ValueError, RepositoryRetrievalError)):
            validate_github_url(url)


# ---------------------------------------------------------------------------
# 4. Branch Validation: Flag Injection Rejection
# ---------------------------------------------------------------------------

def test_rejects_flag_injection_in_branch():
    """Branch names starting with hyphens (flag injection) must be rejected."""
    malicious_branches = [
        "--upload-pack=touch /tmp/pwn",
        "-u",
        "--help",
        "--version",
        "-b",
    ]
    for branch in malicious_branches:
        with pytest.raises((ValueError, RepositoryRetrievalError), match="flag injection"):
            validate_branch_name(branch)


# ---------------------------------------------------------------------------
# 5. Branch Validation: Command Separators Rejection
# ---------------------------------------------------------------------------

def test_rejects_command_separators_in_branch():
    """Branch names containing shell metacharacters must be rejected."""
    malicious_branches = [
        "main; rm -rf /",
        "feature && echo pwned",
        "main | cat /etc/passwd",
        "main`id`",
        "main$PATH",
        "main\nexit",
        "main\0injection",
    ]
    for branch in malicious_branches:
        with pytest.raises((ValueError, RepositoryRetrievalError), match=r"(invalid characters|forbidden control characters)"):
            validate_branch_name(branch)


# ---------------------------------------------------------------------------
# 6. Secret Redaction: GitHub Tokens
# ---------------------------------------------------------------------------

def test_redacts_github_tokens_from_log_messages():
    """GitHub Personal Access Tokens must be redacted from outputs."""
    classic_token = "ghp_ABC1234567890abcdefghijklmnopqrstuvwxyz"
    fine_grained_token = "github_pat_11AAAAAAA_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    log_msg = f"Failed to authenticate using token {classic_token} and fine token {fine_grained_token}."
    redacted = redact_secrets(log_msg)

    assert classic_token not in redacted
    assert fine_grained_token not in redacted
    assert "[REDACTED_SECRET]" in redacted


# ---------------------------------------------------------------------------
# 7. Secret Redaction: Bearer Tokens
# ---------------------------------------------------------------------------

def test_redacts_bearer_tokens_from_log_messages():
    """Bearer authorization headers and tokens must be redacted."""
    raw_header = "Authorization: Bearer secret_jwt_value_1234567890_xyz in request"
    redacted = redact_secrets(raw_header)

    assert "secret_jwt_value_1234567890_xyz" not in redacted
    assert "Bearer [REDACTED_SECRET]" in redacted


# ---------------------------------------------------------------------------
# 8. Secret Redaction: Passwords in URLs
# ---------------------------------------------------------------------------

def test_redacts_passwords_in_urls_from_log_messages():
    """Passwords embedded in URLs must be redacted."""
    raw_url = "git clone https://admin:superSecretPass123@github.com/org/repo.git"
    redacted = redact_secrets(raw_url)

    assert "superSecretPass123" not in redacted
    assert "https://admin:[REDACTED_SECRET]@github.com/org/repo.git" in redacted


# ---------------------------------------------------------------------------
# 9. Workspace Protection: Reject Symlinked Report Path
# ---------------------------------------------------------------------------

def test_rejects_symlinked_report_path(sample_js_repo: Path):
    """Untrusted symlinks for .codeimpact or report paths must be rejected."""
    with patch.object(Path, "is_symlink", return_value=True):
        findings_knip, cov_knip = run_knip_analysis(str(sample_js_repo))
        assert cov_knip.status == "failed"
        assert "symbolic link" in (cov_knip.message or "")

        findings_jscpd, cov_jscpd = run_jscpd_analysis(str(sample_js_repo))
        assert cov_jscpd.status == "failed"
        assert "symbolic link" in (cov_jscpd.message or "")


# ---------------------------------------------------------------------------
# 10. Workspace Protection: Reject Report Path Outside Workspace
# ---------------------------------------------------------------------------

def test_rejects_report_path_outside_workspace(sample_js_repo: Path, tmp_path: Path):
    """Output directories outside the workspace must be rejected as escape attempts."""
    outside_dir = str((tmp_path / "escaped_reports").resolve())

    findings_knip, cov_knip = run_knip_analysis(str(sample_js_repo), output_dir=outside_dir)
    assert cov_knip.status == "failed"
    assert "escapes the repository workspace" in (cov_knip.message or "")

    findings_jscpd, cov_jscpd = run_jscpd_analysis(str(sample_js_repo), output_dir=outside_dir)
    assert cov_jscpd.status == "failed"
    assert "escapes the repository workspace" in (cov_jscpd.message or "")


# ---------------------------------------------------------------------------
# 11. Tool Robustness: Corrupt / Empty jscpd Report Handling
# ---------------------------------------------------------------------------

def test_handles_corrupt_empty_jscpd_report(sample_js_repo: Path):
    """A corrupt or truncated jscpd report file must be handled safely without raising."""
    reports_dir = sample_js_repo / ".codeimpact" / "reports" / "jscpd"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "jscpd-report.json"
    report_file.write_text("{corrupt: [broken json", encoding="utf-8")

    with patch("backend.app.services.static_analysis.jscpd_runner.run_command") as mock_cmd:
        mock_cmd.return_value = CommandResult(
            exit_code=0,
            stdout="Detection time:: 10ms",
            stderr="",
        )
        findings, coverage = run_jscpd_analysis(str(sample_js_repo))
        assert coverage.status == "failed"
        assert "Failed to parse jscpd report JSON" in (coverage.message or "")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# 12. Tool Robustness: Missing jscpd Binary Handling
# ---------------------------------------------------------------------------

def test_handles_missing_jscpd_binary(sample_js_repo: Path):
    """Missing jscpd binary must return failed coverage without crashing."""
    with patch("backend.app.services.static_analysis.jscpd_runner._find_jscpd_executable", return_value="nonexistent_jscpd"):
        with patch("shutil.which", return_value=None):
            findings, coverage = run_jscpd_analysis(str(sample_js_repo))
            assert coverage.status == "failed"
            assert "jscpd executable not found" in (coverage.message or "")
            assert len(findings) == 0


# ---------------------------------------------------------------------------
# 13. Subprocess Safety: Output Truncation for Oversized Outputs (>5MB)
# ---------------------------------------------------------------------------

def test_truncates_oversized_command_output():
    """Command output exceeding 5 MB must be safely truncated with a clear marker."""
    oversized = "X" * (6 * 1024 * 1024)  # 6 MB
    truncated = _truncate_output(oversized)

    assert len(truncated.encode("utf-8")) < 6 * 1024 * 1024
    assert "[OUTPUT TRUNCATED: Exceeded 5 MB limit]" in truncated


# ---------------------------------------------------------------------------
# 14. Workspace Lifecycle: Cleanup on Clone Failure
# ---------------------------------------------------------------------------

def test_cleanup_on_clone_failure():
    """Workspace directories must be completely removed when retrieval fails."""
    analysis_id = "test_cleanup_fail"
    with patch("backend.app.services.repository.github_service.run_command") as mock_cmd:
        mock_cmd.return_value = CommandResult(
            exit_code=128,
            stdout="",
            stderr="fatal: repository 'https://github.com/test/repo' not found",
        )
        with pytest.raises(RepositoryRetrievalError):
            retrieve_repository("https://github.com/test/repo.git", analysis_id=analysis_id)

        # Verify that workspace directory was cleaned up and does not linger
        expected_dir = Path(tempfile.gettempdir()) / "codeimpact" / "workspaces" / analysis_id
        assert not expected_dir.exists()


# ---------------------------------------------------------------------------
# 15. Orchestration Isolation: Knip Failure Does Not Mask jscpd
# ---------------------------------------------------------------------------

def test_orchestration_isolation_knip_failure_does_not_mask_jscpd(sample_js_repo: Path):
    """Knip failure must not prevent jscpd from executing or mask its findings."""
    dummy_jscpd_finding = Finding(
        finding_id="f_dup_001",
        category="duplicate_code",
        title="Duplicate code block",
        file_path="src/index.js",
        start_line=1,
        end_line=5,
        source_tool="jscpd",
        description="Duplicate block detected across 2 locations",
        evidence_class="strong",
        review_risk="unknown",
        evidence=[
            EvidenceItem(
                kind="duplicate_block",
                status="found",
                source="jscpd",
                details="Duplicate code block",
                value={"tokens": 10},
            )
        ],
        metadata={"tokens": 10},
    )

    with patch(
        "backend.app.services.static_analysis.analyzer.run_knip_analysis",
        side_effect=RuntimeError("Knip crashed unexpectedly"),
    ):
        with patch(
            "backend.app.services.static_analysis.analyzer.run_jscpd_analysis",
            return_value=([dummy_jscpd_finding], ToolCoverageItem(status="completed", finding_count=1)),
        ):
            result = analyze_repository(str(sample_js_repo), analysis_id="isolation_test_1")

            assert result["tool_coverage"]["knip"]["status"] == "failed"
            assert "Knip execution error" in result["tool_coverage"]["knip"]["message"]
            assert result["tool_coverage"]["jscpd"]["status"] == "completed"
            assert len(result["findings"]) == 1
            assert result["findings"][0]["finding_id"] == "f_dup_001"


# ---------------------------------------------------------------------------
# 16. Orchestration Isolation: jscpd Failure Does Not Mask Knip
# ---------------------------------------------------------------------------

def test_orchestration_isolation_jscpd_failure_does_not_mask_knip(sample_js_repo: Path):
    """jscpd failure must not prevent Knip from executing or discard Knip findings."""
    dummy_knip_finding = Finding(
        finding_id="f_knip_001",
        category="unused_file",
        title="Unused file",
        file_path="src/unused.js",
        start_line=1,
        end_line=1,
        source_tool="knip",
        description="Unused file detected",
        evidence_class="strong",
        review_risk="unknown",
        evidence=[
            EvidenceItem(
                kind="static_reference_scan",
                status="not_found",
                source="knip",
                details="No static references found",
            )
        ],
        metadata={},
    )

    with patch(
        "backend.app.services.static_analysis.analyzer.run_knip_analysis",
        return_value=([dummy_knip_finding], ToolCoverageItem(status="completed", finding_count=1)),
    ):
        with patch(
            "backend.app.services.static_analysis.analyzer.run_jscpd_analysis",
            side_effect=RuntimeError("jscpd crashed unexpectedly"),
        ):
            result = analyze_repository(str(sample_js_repo), analysis_id="isolation_test_2")

            assert result["tool_coverage"]["knip"]["status"] == "completed"
            assert result["tool_coverage"]["jscpd"]["status"] == "failed"
            assert "jscpd execution error" in result["tool_coverage"]["jscpd"]["message"]
            assert len(result["findings"]) == 1
            assert result["findings"][0]["finding_id"] == "f_knip_001"


# ---------------------------------------------------------------------------
# 17. Tool Fidelity: jscpd Token Count 0 Not Coerced to None/Null
# ---------------------------------------------------------------------------

def test_jscpd_token_count_zero_not_coerced_to_null():
    """jscpd token count of 0 must be preserved as integer 0 and not converted to None."""
    payload = {
        "duplicates": [
            {
                "format": "javascript",
                "lines": 10,
                "tokens": 0,
                "firstFile": {"name": "src/a.js", "start": 1, "end": 10},
                "secondFile": {"name": "src/b.js", "start": 1, "end": 10},
                "fragment": "function foo() {}",
            }
        ]
    }

    findings = normalize_jscpd_findings(payload, repo_root="/fake/repo")
    assert len(findings) == 1
    finding = findings[0]

    # Verify token preservation in metadata and evidence value
    assert finding.metadata["tokens"] == 0
    assert finding.metadata["tokens"] is not None
    assert isinstance(finding.metadata["tokens"], int)
    assert finding.evidence[0].value["tokens"] == 0


# ---------------------------------------------------------------------------
# 18. Knip Trust Boundary: Executable Config Bypassed Safely
# ---------------------------------------------------------------------------

def test_knip_executable_config_detected_and_handled_safely(sample_js_repo: Path):
    """Target repository knip.js/knip.ts must not be executed; fallback to safe partial status."""
    # Create an untrusted executable knip configuration in target repository
    malicious_config = sample_js_repo / "knip.ts"
    malicious_config.write_text("throw new Error('Executed untrusted repository code!');\n", encoding="utf-8")

    with patch("backend.app.services.static_analysis.knip_runner.run_command") as mock_cmd:
        mock_cmd.return_value = CommandResult(
            exit_code=0,
            stdout="{}",
            stderr="",
        )

        findings, coverage = run_knip_analysis(str(sample_js_repo))

        # Command must NOT have passed --config knip.ts
        cmd_args = mock_cmd.call_args[0][0]
        assert "knip.ts" not in cmd_args

        # Coverage must report partial due to bypassing executable config
        assert coverage.status == "partial"
        assert "Executable Knip configuration" in (coverage.message or "")
