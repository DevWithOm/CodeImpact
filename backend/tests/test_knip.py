"""Comprehensive test suite for Knip integration, version detection, and unused code analysis."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.finding import Finding
from backend.app.services.static_analysis.knip_runner import (
    get_knip_version,
    run_knip,
    run_knip_analysis,
)
from backend.app.services.static_analysis.normalizer import normalize_knip_findings
from backend.app.utils.subprocess_runner import CommandResult


def test_1_knip_version_detection():
    """Verify Knip CLI version detection returns expected 5.45.0 version."""
    version = get_knip_version()
    assert version != "unknown"
    assert version.startswith("5.")


def test_2_successful_tool_execution():
    """Verify run_knip executes successfully against controlled fixture."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_knip(fixture_path)

    assert "findings" in result
    assert "tool_coverage" in result
    coverage = result["tool_coverage"]["knip"]
    assert coverage["status"] == "completed"
    assert coverage["finding_count"] >= 3
    assert len(result["findings"]) == coverage["finding_count"]


def test_3_unused_file_detection():
    """Verify unused files (unused_file.ts) are detected as unused_file."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_knip(fixture_path)

    unused_files = [f for f in result["findings"] if f["category"] == "unused_file"]
    file_paths = [f["file_path"] for f in unused_files]

    assert any("unused_file.ts" in p for p in file_paths)
    for f in unused_files:
        assert f["source_tool"] == "knip"
        assert f["start_line"] is None
        assert f["end_line"] is None
        assert f["review_risk"] == "unknown"


def test_4_unused_export_detection():
    """Verify unused export (unusedHelper) is detected as unused_export with line numbers."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_knip(fixture_path)

    unused_exports = [f for f in result["findings"] if f["category"] == "unused_export"]
    symbols = {f["symbol"]: f for f in unused_exports}

    assert "unusedHelper" in symbols
    finding = symbols["unusedHelper"]
    assert "utils.ts" in finding["file_path"]
    assert finding["start_line"] == 5
    assert finding["source_tool"] == "knip"
    assert finding["evidence_class"] == "inconclusive"


def test_5_unused_dependency_detection():
    """Verify unused dependency (lodash) is detected as unused_dependency in package.json."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_knip(fixture_path)

    unused_deps = [f for f in result["findings"] if f["category"] == "unused_dependency"]
    dep_names = {f["symbol"]: f for f in unused_deps}

    assert "lodash" in dep_names
    finding = dep_names["lodash"]
    assert finding["file_path"] == "package.json"
    assert finding["source_tool"] == "knip"


def test_6_referenced_export_not_flagged():
    """Verify that usedHelper (imported and used in index.ts) is NOT flagged as unused."""
    fixture_path = str(Path("fixtures/sample-js-repository").resolve())
    result = run_knip(fixture_path)

    symbols = [f.get("symbol") for f in result["findings"]]
    assert "usedHelper" not in symbols


def test_7_json_parsing_and_normalization():
    """Verify normalization of Knip JSON structure across different issue types."""
    raw_knip = {
        "files": ["src/dead.ts"],
        "issues": [
            {
                "file": "package.json",
                "dependencies": [{"name": "fake-dep", "line": 20, "col": 2}],
                "devDependencies": [],
                "exports": [{"name": "orphanedFn", "line": 55, "col": 1}],
                "types": [{"name": "OrphanedType", "line": 70, "col": 1}],
            }
        ],
    }

    findings = normalize_knip_findings(raw_knip, repo_root="/test/root")
    assert len(findings) == 4

    categories = {f.category for f in findings}
    assert categories == {"unused_file", "unused_dependency", "unused_export"}

    for f in findings:
        assert isinstance(f, Finding)
        assert f.source_tool == "knip"
        assert f.review_risk == "unknown"


def test_8_missing_configuration_handling(tmp_path):
    """Verify missing package.json results in partial status rather than crashing."""
    repo = tmp_path / "no_package_json_repo"
    repo.mkdir()
    src = repo / "src"
    src.mkdir()
    (src / "test.ts").write_text("export const x = 1;")

    findings, coverage = run_knip_analysis(str(repo))
    assert coverage.status == "partial"
    assert "package.json" in coverage.message
    assert len(findings) == 0


def test_9_malformed_json_handling(tmp_path):
    """Verify that malformed JSON from tool results in failed status."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "mock"}')
    (repo / "test.ts").write_text("console.log(1);")

    # Mock run_command returning invalid JSON
    mock_result = CommandResult(exit_code=0, stdout="Not a JSON output", stderr="")
    with patch("backend.app.services.static_analysis.knip_runner.run_command", return_value=mock_result):
        findings, coverage = run_knip_analysis(str(repo))
        assert coverage.status == "failed"
        assert "Failed to parse" in coverage.message
        assert len(findings) == 0


def test_10_timeout_handling(tmp_path):
    """Verify timeout is captured as failed status and does not pretend zero findings."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "mock"}')
    (repo / "test.ts").write_text("console.log(1);")

    mock_result = CommandResult(exit_code=-1, stdout="", stderr="timed out", timed_out=True)
    with patch("backend.app.services.static_analysis.knip_runner.run_command", return_value=mock_result):
        findings, coverage = run_knip_analysis(str(repo))
        assert coverage.status == "failed"
        assert "timed out" in coverage.message
        assert len(findings) == 0


def test_11_non_zero_exit_status(tmp_path):
    """Verify tool crashes (exit code != 0 without valid output) are reported as failed."""
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "mock"}')
    (repo / "test.ts").write_text("console.log(1);")

    mock_result = CommandResult(exit_code=2, stdout="", stderr="Internal Knip error occurred")
    with patch("backend.app.services.static_analysis.knip_runner.run_command", return_value=mock_result):
        findings, coverage = run_knip_analysis(str(repo))
        assert coverage.status == "failed"
        assert "Knip failed with exit code 2" in coverage.message
        assert len(findings) == 0


def test_12_empty_repo_skipped(tmp_path):
    """Verify repositories with no JS/TS files are cleanly skipped."""
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    (empty_repo / "README.md").write_text("# Pure Docs")

    findings, coverage = run_knip_analysis(str(empty_repo))
    assert coverage.status == "skipped"
    assert "No JavaScript or TypeScript files" in coverage.message
    assert len(findings) == 0
