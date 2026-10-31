"""Unit tests for static test framework detection."""

import json
from pathlib import Path
import pytest

from backend.app.services.dependency_impact.test_framework_detector import (
    detect_test_frameworks,
)


def test_detect_jest_framework(tmp_path: Path):
    # Setup package.json and jest.config.js
    pkg = {
        "name": "sample",
        "devDependencies": {"jest": "^29.0.0", "@types/jest": "^29.0.0"},
        "scripts": {"test": "jest"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "jest.config.js").write_text("module.exports = {};", encoding="utf-8")

    frameworks = detect_test_frameworks(str(tmp_path))
    assert len(frameworks) == 1
    fw = frameworks[0]
    assert fw["name"] == "jest"
    assert fw["confidence"] == "high"
    assert any("jest.config.js" in e for e in fw["evidence"])
    assert any("package.json dependency: jest" in e for e in fw["evidence"])


def test_detect_vitest_framework(tmp_path: Path):
    pkg = {
        "name": "sample-vitest",
        "devDependencies": {"vitest": "^1.0.0"},
        "scripts": {"test": "vitest run"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "vitest.config.ts").write_text("export default {};", encoding="utf-8")

    frameworks = detect_test_frameworks(str(tmp_path))
    assert len(frameworks) == 1
    fw = frameworks[0]
    assert fw["name"] == "vitest"
    assert fw["confidence"] == "high"
    assert any("vitest.config.ts" in e for e in fw["evidence"])


def test_detect_playwright_and_cypress(tmp_path: Path):
    pkg = {
        "name": "e2e-project",
        "devDependencies": {"@playwright/test": "^1.40.0", "cypress": "^13.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "playwright.config.ts").write_text("export default {};", encoding="utf-8")
    (tmp_path / "cypress.config.js").write_text("module.exports = {};", encoding="utf-8")

    frameworks = detect_test_frameworks(str(tmp_path))
    names = [f["name"] for f in frameworks]
    assert "playwright" in names
    assert "cypress" in names


def test_detect_pytest_framework(tmp_path: Path):
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests", encoding="utf-8")

    frameworks = detect_test_frameworks(str(tmp_path))
    assert len(frameworks) == 1
    assert frameworks[0]["name"] == "pytest"
    assert frameworks[0]["confidence"] == "high"


def test_detect_frameworks_empty_repo(tmp_path: Path):
    frameworks = detect_test_frameworks(str(tmp_path))
    assert frameworks == []


def test_detect_frameworks_none_path():
    assert detect_test_frameworks(None) == []
    assert detect_test_frameworks("") == []


def test_detect_frameworks_malformed_package_json(tmp_path: Path):
    (tmp_path / "package.json").write_text("{ malformed json ", encoding="utf-8")
    # Must not crash, should handle gracefully
    frameworks = detect_test_frameworks(str(tmp_path))
    assert isinstance(frameworks, list)

