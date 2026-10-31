"""Tests for jscpd duplication analysis integration and normalization."""

from pathlib import Path
import pytest

from backend.app.services.static_analysis.jscpd_runner import run_jscpd_analysis
from backend.app.services.static_analysis.normalizer import normalize_jscpd_findings


def test_normalize_jscpd_findings_schema():
    raw_sample = {
        "duplicates": [
            {
                "format": "typescript",
                "lines": 12,
                "fragment": "function duplicateMethod() { ... }",
                "firstFile": {
                    "name": "src/moduleA.ts",
                    "start": 10,
                    "end": 22,
                    "startLoc": {"line": 10, "column": 1},
                    "endLoc": {"line": 22, "column": 2},
                },
                "secondFile": {
                    "name": "src/moduleB.ts",
                    "start": 30,
                    "end": 42,
                    "startLoc": {"line": 30, "column": 1},
                    "endLoc": {"line": 42, "column": 2},
                },
            }
        ]
    }

    findings = normalize_jscpd_findings(raw_sample, repo_root="/mock/repo")

    assert len(findings) == 1
    f = findings[0]
    assert f.category == "duplicate_code"
    assert f.file_path == "src/moduleA.ts"
    assert f.start_line == 10
    assert f.end_line == 22
    assert f.source_tool == "jscpd"
    assert f.evidence_class == "strong"
    assert f.review_risk == "unknown"
    assert len(f.evidence) >= 1
    assert f.evidence[0].kind == "duplicate_block"
    assert f.metadata["duplicate_locations"][0]["file_path"] == "src/moduleB.ts"
    assert f.metadata["duplicate_locations"][0]["start_line"] == 30


def test_run_jscpd_against_fixture():
    fixture_path = Path("fixtures/sample-js-repository").resolve()
    assert fixture_path.exists()

    findings, coverage = run_jscpd_analysis(str(fixture_path))

    assert coverage.status == "completed"
    assert coverage.finding_count >= 1
    assert len(findings) >= 1

    dup = findings[0]
    assert dup.category == "duplicate_code"
    assert dup.source_tool == "jscpd"
    # Service A and Service B should be connected in duplication
    assert "serviceA.ts" in dup.file_path or "serviceB.ts" in dup.file_path
