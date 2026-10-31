"""Static test framework detection engine for CodeImpact.

Inspects configuration files and package metadata to identify testing frameworks
deterministically without executing any code.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Framework signatures mapping framework name to config file patterns and package dependencies
FRAMEWORK_SIGNATURES: dict[str, dict[str, Any]] = {
    "vitest": {
        "config_files": [
            "vitest.config.ts",
            "vitest.config.js",
            "vitest.config.mts",
            "vitest.config.mjs",
        ],
        "package_deps": ["vitest", "@vitest/coverage-v8", "@vitest/ui"],
        "script_keywords": ["vitest"],
    },
    "jest": {
        "config_files": [
            "jest.config.js",
            "jest.config.ts",
            "jest.config.json",
            "jest.config.mjs",
            "jest.config.cjs",
        ],
        "package_deps": ["jest", "ts-jest", "babel-jest", "@types/jest"],
        "script_keywords": ["jest"],
    },
    "playwright": {
        "config_files": [
            "playwright.config.ts",
            "playwright.config.js",
            "playwright.config.mjs",
        ],
        "package_deps": ["@playwright/test", "playwright"],
        "script_keywords": ["playwright test", "playwright"],
    },
    "cypress": {
        "config_files": [
            "cypress.config.ts",
            "cypress.config.js",
            "cypress.config.mjs",
            "cypress.json",
        ],
        "package_deps": ["cypress"],
        "script_keywords": ["cypress open", "cypress run"],
    },
    "mocha": {
        "config_files": [
            ".mocharc.json",
            ".mocharc.js",
            ".mocharc.yaml",
            ".mocharc.yml",
            "mocha.opts",
        ],
        "package_deps": ["mocha", "@types/mocha"],
        "script_keywords": ["mocha"],
    },
    "pytest": {
        "config_files": [
            "pytest.ini",
            "conftest.py",
        ],
        "file_patterns": ["conftest.py"],
        "script_keywords": ["pytest"],
    },
}


def read_json_safely(file_path: Path) -> dict[str, Any]:
    """Read a JSON file safely without throwing exceptions on malformed content."""
    try:
        if file_path.exists() and file_path.is_file():
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.debug("Could not parse JSON from %s: %s", file_path, e)
    return {}


def detect_test_frameworks(repo_path: str | Path | None) -> list[dict[str, Any]]:
    """Statically detect test frameworks present in the repository workspace.

    Args:
        repo_path: Absolute local path to repository workspace.

    Returns:
        List of framework evidence dictionaries:
        [{'name': 'vitest', 'confidence': 'high', 'evidence': [...]}]
    """
    if not repo_path:
        return []

    path_obj = Path(repo_path).resolve()
    if not path_obj.exists() or not path_obj.is_dir():
        return []

    detected: list[dict[str, Any]] = []

    # 1. Parse package.json if present
    pkg_json_path = path_obj / "package.json"
    pkg_data = read_json_safely(pkg_json_path) if pkg_json_path.exists() else {}

    all_deps: set[str] = set()
    if pkg_data:
        deps = pkg_data.get("dependencies") or {}
        dev_deps = pkg_data.get("devDependencies") or {}
        peer_deps = pkg_data.get("peerDependencies") or {}
        if isinstance(deps, dict):
            all_deps.update(deps.keys())
        if isinstance(dev_deps, dict):
            all_deps.update(dev_deps.keys())
        if isinstance(peer_deps, dict):
            all_deps.update(peer_deps.keys())

    scripts = pkg_data.get("scripts") or {}
    script_texts = [str(v).lower() for v in scripts.values()] if isinstance(scripts, dict) else []

    # Check pyproject.toml / pytest.ini for Python pytest
    pyproject_path = path_obj / "pyproject.toml"
    has_pytest_in_pyproject = False
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                if "[tool.pytest" in content or "pytest" in content:
                    has_pytest_in_pyproject = True
        except Exception:
            pass

    # Evaluate each framework
    for fw_name, sig in FRAMEWORK_SIGNATURES.items():
        evidence_items: list[str] = []
        has_config_file = False
        has_dep = False
        has_script = False

        # Check config files
        for cfg_name in sig.get("config_files", []):
            cfg_path = path_obj / cfg_name
            if cfg_path.exists() and cfg_path.is_file():
                has_config_file = True
                evidence_items.append(f"Configuration file present: {cfg_name}")

        # Check package dependencies
        for dep in sig.get("package_deps", []):
            if dep in all_deps:
                has_dep = True
                evidence_items.append(f"package.json dependency: {dep}")

        # Check scripts
        for kw in sig.get("script_keywords", []):
            for st in script_texts:
                if kw in st:
                    has_script = True
                    evidence_items.append(f"Test script references: '{kw}'")
                    break

        # Pytest special check
        if fw_name == "pytest" and has_pytest_in_pyproject:
            has_config_file = True
            evidence_items.append("pyproject.toml contains pytest configuration")

        if evidence_items:
            # Determine confidence
            if has_config_file or (has_dep and has_script):
                confidence = "high"
            elif has_dep or has_script:
                confidence = "medium"
            else:
                confidence = "low"

            detected.append({
                "name": fw_name,
                "confidence": confidence,
                "evidence": evidence_items,
            })

    # Sort deterministically by framework name
    detected.sort(key=lambda d: d["name"])
    return detected

