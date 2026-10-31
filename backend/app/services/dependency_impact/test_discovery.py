"""Static test file discovery and classification engine for CodeImpact.

Discovers candidate test files in JavaScript/TypeScript (and supported backend)
repositories using deterministic static naming and directory conventions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
from typing import Any

from backend.app.services.dependency_impact.madge_runner import normalize_repo_relative_path

logger = logging.getLogger(__name__)

# Test Classification Enums
TEST_TYPE_UNIT = "unit_test"
TEST_TYPE_INTEGRATION = "integration_test"
TEST_TYPE_E2E = "e2e_test"
TEST_TYPE_CONFIG = "test_config"
TEST_TYPE_UNKNOWN = "unknown_test_type"

# Directories that are ignored during scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    "coverage",
    ".next",
    ".cache",
    ".pytest_cache",
}

# Regex for delimited test filename patterns (e.g. .test.ts, .spec.jsx, test_auth.py, auth_test.py)
TEST_DELIMITED_PATTERN = re.compile(
    r"(^|/)(([^/]+(\.|\-|_)(test|spec)\.[a-zA-Z0-9]+)|(test_[^/]+\.[a-zA-Z0-9]+)|([^/]+_test\.[a-zA-Z0-9]+))$",
    re.IGNORECASE,
)

# Regex for PascalCase/CamelCase Java style (e.g. PaymentTest.java, UserTest.ts) - case-sensitive
TEST_CAMELCASE_PATTERN = re.compile(
    r"(^|/)[A-Z][a-zA-Z0-9]*[a-z0-9]Test\.[a-zA-Z0-9]+$"
)

# Test directories that imply test context
TEST_DIR_PATTERN = re.compile(
    r"(^|/)(__tests__|tests?|spec|e2e|integration|unit)(/|$)",
    re.IGNORECASE,
)

# Supported source & test extensions
TEST_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".java"
}


def is_test_file(path_str: str) -> bool:
    """Determine whether a repository-relative path represents a test file.

    Evaluates naming conventions (.test., .spec., test_*, *_test) and test directories.

    Args:
        path_str: Normalized repository-relative POSIX path.

    Returns:
        True if the path represents a test file, False otherwise.
    """
    if not path_str or not isinstance(path_str, str):
        return False

    cleaned = path_str.strip().replace("\\", "/")

    # Check for ignored directories in path
    segments = set(cleaned.split("/"))
    if segments.intersection(IGNORED_DIRS):
        return False

    ext = Path(cleaned).suffix.lower()
    if ext not in TEST_EXTENSIONS:
        return False

    filename = Path(cleaned).name

    # Helper / mock / fixture / data files or subdirectories are excluded even if in test directories
    if re.search(r"(^|/)((fixtures?|mocks?|helpers?|stubs?|utils?)(/|$))", cleaned, re.IGNORECASE):
        # Exclude unless explicitly named as a test
        if not (TEST_DELIMITED_PATTERN.search(cleaned) or TEST_CAMELCASE_PATTERN.search(cleaned)):
            return False

    if re.search(r"(\.|\-|_|^)(fixture|mock|helper|util|setup|stub)", filename, re.IGNORECASE):
        # Exclude unless explicitly named as a test
        if not (TEST_DELIMITED_PATTERN.search(cleaned) or TEST_CAMELCASE_PATTERN.search(cleaned)):
            return False

    # 1. Matches test filename patterns
    if TEST_DELIMITED_PATTERN.search(cleaned) or TEST_CAMELCASE_PATTERN.search(cleaned):
        return True

    # 2. Inside a dedicated test directory with valid extension
    if TEST_DIR_PATTERN.search(cleaned):
        # If in a test directory and has code extension, it is considered a test file
        return True

    return False


def classify_test_type(path_str: str) -> str:
    """Classify the likely test type based on path and filename semantics.

    Args:
        path_str: Normalized repository-relative POSIX path.

    Returns:
        One of: 'unit_test', 'integration_test', 'e2e_test', 'test_config', 'unknown_test_type'
    """
    if not path_str or not isinstance(path_str, str):
        return TEST_TYPE_UNKNOWN

    cleaned = path_str.strip().replace("\\", "/").lower()
    filename = Path(cleaned).name

    # Config / Setup files
    if re.search(r"(setup[-_]?tests?|jest\.setup|test[-_]?setup|\.config)\.[a-z0-9]+$", filename):
        return TEST_TYPE_CONFIG

    # E2E test signals
    if "/e2e/" in cleaned or "cypress/" in cleaned or "playwright/" in cleaned or ".e2e." in filename:
        return TEST_TYPE_E2E

    # Integration test signals
    if "/integration/" in cleaned or ".integration." in filename or ".it." in filename:
        return TEST_TYPE_INTEGRATION

    # Unit test signals
    if (
        "/unit/" in cleaned
        or ".test." in filename
        or ".spec." in filename
        or "/__tests__/" in cleaned
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    ):
        return TEST_TYPE_UNIT

    if "/tests/" in cleaned or "/test/" in cleaned or "/spec/" in cleaned:
        return TEST_TYPE_UNIT

    return TEST_TYPE_UNKNOWN


def discover_test_files_from_nodes(nodes: list[str] | set[str] | list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Extract and classify test files present in dependency graph nodes.

    Args:
        nodes: List or set of graph node paths or node dictionaries.

    Returns:
        Deduplicated list of dictionaries with 'file_path' and 'test_type'.
    """
    if not nodes:
        return []

    discovered: dict[str, str] = {}

    for item in nodes:
        raw_path = None
        if isinstance(item, str):
            raw_path = item
        elif isinstance(item, dict):
            raw_path = item.get("file_path") or item.get("id")

        if not raw_path:
            continue

        norm_path = normalize_repo_relative_path(raw_path)
        if norm_path and is_test_file(norm_path):
            discovered[norm_path] = classify_test_type(norm_path)

    results = [
        {"file_path": p, "test_type": t}
        for p, t in sorted(discovered.items())
    ]
    return results


def scan_repository_for_tests(repo_path: str | Path | None) -> list[dict[str, str]]:
    """Statically scan repository filesystem to discover test files.

    Safely walks the workspace directory without executing any code.

    Args:
        repo_path: Absolute local path to repository workspace.

    Returns:
        Deduplicated list of dictionaries with 'file_path' and 'test_type'.
    """
    if not repo_path:
        return []

    path_obj = Path(repo_path).resolve()
    if not path_obj.exists() or not path_obj.is_dir():
        return []

    discovered: dict[str, str] = {}

    try:
        for root, dirs, files in os.walk(str(path_obj), topdown=True):
            # Prune ignored directories in-place to avoid unnecessary traversal
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            rel_root = os.path.relpath(root, str(path_obj)).replace("\\", "/")
            if rel_root == ".":
                rel_root = ""

            for file in files:
                rel_file = f"{rel_root}/{file}" if rel_root else file
                norm_file = normalize_repo_relative_path(rel_file)
                if norm_file and is_test_file(norm_file):
                    discovered[norm_file] = classify_test_type(norm_file)
    except Exception as e:
        logger.warning("Error during static test discovery in %s: %s", repo_path, e)

    return [
        {"file_path": p, "test_type": t}
        for p, t in sorted(discovered.items())
    ]


def discover_test_files(
    repo_path: str | Path | None = None,
    graph_nodes: list[str] | set[str] | list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Discover all test files combining graph nodes and static repository scanning.

    Deduplicates results and sorts deterministically.

    Args:
        repo_path: Optional repository root path.
        graph_nodes: Optional graph nodes list or set.

    Returns:
        List of candidate test dictionaries: [{'file_path': '...', 'test_type': '...'}]
    """
    tests_by_path: dict[str, str] = {}

    # 1. Discover from graph nodes
    for item in discover_test_files_from_nodes(graph_nodes):
        tests_by_path[item["file_path"]] = item["test_type"]

    # 2. Discover from filesystem if repo_path provided
    if repo_path:
        for item in scan_repository_for_tests(repo_path):
            tests_by_path[item["file_path"]] = item["test_type"]

    return [
        {"file_path": p, "test_type": t}
        for p, t in sorted(tests_by_path.items())
    ]
