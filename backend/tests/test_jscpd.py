"""Comprehensive test suite for jscpd duplication analysis, version detection, and normalisation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.finding import Finding
from backend.app.services.static_analysis.jscpd_runner import (
    get_jscpd_version,
    run_jscpd,
    run_jscpd_analysis,
)
from backend.app.services.static_analysis.normalizer import normalize_jscpd_findings
from backend.app.utils.subprocess_runner import CommandResult


def test_1_jscpd_version_detection():
    """Verify jscpd version detection returns 4.0.5."""
    version = get_jscpd_version()
    assert version != "unknown"
    assert version.startswith("4.")


def test_2_successful_jscpd_execution():
    """Verify run_jscpd runs successfully against the controlled fixture."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_jscpd(fixture_path)

    assert "findings" in result
    assert "tool_coverage" in result
    coverage = result["tool_coverage"]["jscpd"]
    assert coverage["status"] == "completed"
    assert coverage["finding_count"] >= 1
    assert len(result["findings"]) == coverage["finding_count"]


def test_3_detection_of_actual_duplicated_code_block():
    """Verify that jscpd identifies the duplicate block between service files."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_jscpd(fixture_path)

    findings = result["findings"]
    dup_finding = next((f for f in findings if f["category"] == "duplicate_code"), None)
    assert dup_finding is not None
    assert dup_finding["source_tool"] == "jscpd"
    assert dup_finding["evidence_class"] == "strong"
    assert dup_finding["review_risk"] == "unknown"


def test_4_no_finding_for_non_duplicated_fixture(tmp_path):
    """Verify a repository with no duplicate code returns completed with 0 findings."""
    clean_repo = tmp_path / "clean_repo"
    clean_repo.mkdir()
    (clean_repo / "package.json").write_text('{"name": "clean"}')
    src = clean_repo / "src"
    src.mkdir()
    (src / "fileA.ts").write_text("export const a = 1;\nconsole.log(a);")
    (src / "fileB.ts").write_text("export const b = 'unique string';\nfunction foo() { return true; }")

    findings, coverage = run_jscpd_analysis(str(clean_repo))
    assert coverage.status == "completed"
    assert coverage.finding_count == 0
    assert len(findings) == 0


def test_5_correct_preservation_of_file_paths():
    """Verify that file paths are normalized and relative to repository root."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_jscpd(fixture_path)

    finding = result["findings"][0]
    assert finding["file_path"].startswith("src/")
    assert not finding["file_path"].startswith("fixtures/")
    assert not Path(finding["file_path"]).is_absolute()


def test_6_correct_preservation_of_line_numbers():
    """Verify start and end line numbers are preserved exactly as reported."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_jscpd(fixture_path)

    finding = result["findings"][0]
    assert finding["start_line"] == 1
    assert finding["end_line"] == 9
    for loc in finding["metadata"]["duplicate_locations"]:
        assert loc["start_line"] == 1
        assert loc["end_line"] == 9


def test_7_multiple_matching_locations_in_duplicate_group():
    """Verify that duplicates across 3 files (serviceA, serviceB, serviceC) are grouped."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_jscpd(fixture_path)

    finding = result["findings"][0]
    matches = finding["metadata"]["duplicate_locations"]
    # serviceA matches both serviceB and serviceC
    matching_paths = [m["file_path"] for m in matches]
    assert len(matching_paths) >= 2
    assert any("serviceB.ts" in p for p in matching_paths)
    assert any("serviceC.ts" in p for p in matching_paths)
    assert finding["metadata"]["duplicate_group_size"] >= 3


def test_8_correct_normalisation_schema():
    """Verify all fields match the Pydantic Finding schema."""
    raw_jscpd = {
        "duplicates": [
            {
                "format": "javascript",
                "lines": 15,
                "tokens": 80,
                "fragment": "function calculateTotal() { return items.reduce(...); }",
                "firstFile": {
                    "name": "src/billing.js",
                    "start": 20,
                    "end": 35,
                },
                "secondFile": {
                    "name": "src/checkout.js",
                    "start": 50,
                    "end": 65,
                },
            }
        ]
    }

    findings = normalize_jscpd_findings(raw_jscpd, repo_root="/test/root")
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, Finding)
    assert f.finding_id.startswith("f_dup_")
    assert f.category == "duplicate_code"
    assert f.title == "Duplicate code block"
    assert f.file_path == "src/billing.js"
    assert f.start_line == 20
    assert f.end_line == 35
    assert f.source_tool == "jscpd"
    assert f.evidence_class == "strong"
    assert f.review_risk == "unknown"
    assert len(f.evidence) == 1
    assert f.evidence[0].kind == "duplicate_block"
    assert f.evidence[0].status == "found"
    assert f.metadata["duplicate_locations"][0]["file_path"] == "src/checkout.js"


def test_9_stable_finding_ids_for_identical_input():
    """Verify that identical analysis inputs produce identical, reproducible finding IDs."""
    raw_jscpd = {
        "duplicates": [
            {
                "format": "typescript",
                "lines": 8,
                "firstFile": {"name": "src/a.ts", "start": 10, "end": 18},
                "secondFile": {"name": "src/b.ts", "start": 20, "end": 28},
            }
        ]
    }

    findings_1 = normalize_jscpd_findings(raw_jscpd, repo_root="/repo")
    findings_2 = normalize_jscpd_findings(raw_jscpd, repo_root="/repo")

    assert findings_1[0].finding_id == findings_2[0].finding_id


def test_10_malformed_json_handling(tmp_path):
    """Verify malformed JSON from jscpd returns status failed."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "test.ts").write_text("console.log(1);")

    # Mock jscpd report with invalid json
    rep_dir = repo / ".codeimpact" / "reports" / "jscpd"
    rep_dir.mkdir(parents=True)
    (rep_dir / "jscpd-report.json").write_text("{ unclosed json content")

    mock_result = CommandResult(exit_code=0, stdout="", stderr="")
    with patch("backend.app.services.static_analysis.jscpd_runner.run_command", return_value=mock_result):
        findings, coverage = run_jscpd_analysis(str(repo))
        assert coverage.status == "failed"
        assert "Failed to parse" in coverage.message
        assert len(findings) == 0


def test_11_missing_report_handling(tmp_path):
    """Verify missing report output is reported as failed."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "test.ts").write_text("console.log(1);")

    # Command exited 0 but no report file created
    mock_result = CommandResult(exit_code=0, stdout="No report generated", stderr="")
    with patch("backend.app.services.static_analysis.jscpd_runner.run_command", return_value=mock_result):
        findings, coverage = run_jscpd_analysis(str(repo))
        assert coverage.status == "failed"
        assert "not generated" in coverage.message
        assert len(findings) == 0


def test_12_timeout_handling(tmp_path):
    """Verify timeout is captured as failed status and does not pretend zero findings."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "test.ts").write_text("console.log(1);")

    mock_result = CommandResult(exit_code=-1, stdout="", stderr="timed out", timed_out=True)
    with patch("backend.app.services.static_analysis.jscpd_runner.run_command", return_value=mock_result):
        findings, coverage = run_jscpd_analysis(str(repo))
        assert coverage.status == "failed"
        assert "timed out" in coverage.message
        assert len(findings) == 0


def test_13_non_zero_exit_status(tmp_path):
    """Verify tool crashes (exit code != 0 without report) return status failed."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "test.ts").write_text("console.log(1);")

    mock_result = CommandResult(exit_code=1, stdout="", stderr="Fatal jscpd crash")
    with patch("backend.app.services.static_analysis.jscpd_runner.run_command", return_value=mock_result):
        findings, coverage = run_jscpd_analysis(str(repo))
        assert coverage.status == "failed"
        assert "jscpd failed with exit code 1" in coverage.message
        assert len(findings) == 0


def test_14_empty_repository_skipped(tmp_path):
    """Verify repositories with no JS/TS files are cleanly skipped."""
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    (empty_repo / "README.md").write_text("# Documentation only")

    findings, coverage = run_jscpd_analysis(str(empty_repo))
    assert coverage.status == "skipped"
    assert "No JavaScript or TypeScript files" in coverage.message
    assert len(findings) == 0


def test_15_knip_and_jscpd_integration_in_analyzer():
    """Verify both Knip and jscpd run together in analyzer without conflict."""
    from backend.app.services.static_analysis.analyzer import analyze_repository

    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = analyze_repository(fixture_path, "an_phase3_test")

    assert "findings" in result
    assert "tool_coverage" in result
    coverage = result["tool_coverage"]

    # Both tools must be completed
    assert coverage["knip"]["status"] == "completed"
    assert coverage["jscpd"]["status"] == "completed"

    tools = {f["source_tool"] for f in result["findings"]}
    assert "knip" in tools
    assert "jscpd" in tools

    categories = {f["category"] for f in result["findings"]}
    assert "duplicate_code" in categories
    assert "unused_file" in categories or "unused_export" in categories
