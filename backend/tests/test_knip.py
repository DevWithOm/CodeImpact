"""Tests for Knip static analysis integration and normalization."""

import json
from pathlib import Path
import pytest

from backend.app.services.static_analysis.knip_runner import run_knip_analysis
from backend.app.services.static_analysis.normalizer import normalize_knip_findings


def test_normalize_knip_findings_schema():
    raw_sample = {
        "files": ["src/legacy.ts"],
        "issues": [
            {
                "file": "package.json",
                "dependencies": [{"name": "unused-pkg", "line": 15, "col": 4}],
                "devDependencies": [],
                "exports": [{"name": "abandonedHelper", "line": 42, "col": 1}],
                "types": [{"name": "DeprecatedConfig", "line": 80, "col": 1}],
            }
        ],
    }

    findings = normalize_knip_findings(raw_sample, repo_root="/mock/repo")

    assert len(findings) == 4
    categories = {f.category for f in findings}
    assert "unused_file" in categories
    assert "unused_dependency" in categories
    assert "unused_export" in categories

    # Verify unused file
    file_finding = next(f for f in findings if f.category == "unused_file")
    assert file_finding.file_path == "src/legacy.ts"
    assert file_finding.source_tool == "knip"
    assert file_finding.review_risk == "unknown"
    assert file_finding.evidence_class == "inconclusive"
    assert file_finding.start_line is None

    # Verify unused export
    export_finding = next(f for f in findings if f.symbol == "abandonedHelper")
    assert export_finding.category == "unused_export"
    assert export_finding.start_line == 42
    assert export_finding.source_tool == "knip"

    # Verify unused dependency
    dep_finding = next(f for f in findings if f.symbol == "unused-pkg")
    assert dep_finding.category == "unused_dependency"
    assert dep_finding.file_path == "package.json"
    assert dep_finding.start_line == 15


def test_run_knip_against_fixture():
    fixture_path = Path("fixtures/sample-js-repository").resolve()
    assert fixture_path.exists()

    findings, coverage = run_knip_analysis(str(fixture_path))

    assert coverage.status in ("completed", "partial")
    assert coverage.finding_count > 0
    assert len(findings) == coverage.finding_count

    # Knip should detect unused files or dependencies in fixture
    file_paths = [f.file_path for f in findings]
    assert any("serviceB.ts" in p or "unused_file.ts" in p or "package.json" in p for p in file_paths)
