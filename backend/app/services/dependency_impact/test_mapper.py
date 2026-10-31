"""Test impact mapping engine for CodeImpact.

Associates source files with candidate test files using:
1. Direct static import edges in the dependency graph (mapping_status: 'direct')
2. Bounded transitive reachability in the dependency graph (mapping_status: 'heuristic')
3. Deterministic filename, suffix, and directory heuristics (mapping_status: 'heuristic')
"""

from __future__ import annotations

from collections import deque
import logging
from pathlib import Path
import re
from typing import Any

from backend.app.schemas.test_impact import FindingTestImpact, TestCandidate, TestImpactSummary
from backend.app.services.dependency_impact.test_discovery import classify_test_type, is_test_file

logger = logging.getLogger(__name__)

# Maximum depth for transitive test reachability traversal
MAX_TEST_IMPACT_DEPTH = 5


def extract_stem(file_path: str) -> str:
    """Extract canonical module stem from a file path.

    Examples:
        src/services/payment.ts -> payment
        tests/payment.test.ts -> payment
        src/components/Button.spec.tsx -> button
        test_auth.py -> auth
        auth_test.py -> auth
    """
    cleaned = file_path.replace("\\", "/")
    filename = Path(cleaned).name.lower()

    # Strip test indicators
    filename = re.sub(r"(\.|\-|_)(test|spec|integration|e2e|it)\.[a-z0-9]+$", "", filename)
    filename = re.sub(r"^test_", "", filename)
    filename = re.sub(r"_test\.[a-z0-9]+$", "", filename)

    # Strip final extension if any remains
    stem = Path(filename).stem
    return stem.lower()


def find_direct_test_dependants(
    source_file: str,
    incoming_edges: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Identify test files that directly import the source file.

    In the graph: T -> S means T imports S.
    So T is in incoming_edges[S].

    Args:
        source_file: Normalized repository-relative path of source file.
        incoming_edges: Index mapping target -> incoming edges.

    Returns:
        List of candidate test dictionaries with mapping_status='direct'.
    """
    direct_candidates: list[dict[str, Any]] = []
    seen_tests: set[str] = set()

    edges = incoming_edges.get(source_file, [])
    for edge in edges:
        src = edge.get("source")
        if not src or not isinstance(src, str):
            continue

        if is_test_file(src) and src not in seen_tests:
            seen_tests.add(src)
            test_type = classify_test_type(src)
            direct_candidates.append({
                "file_path": src,
                "test_type": test_type,
                "mapping_status": "direct",
                "evidence_type": "static_import",
                "dependency_path": [src, source_file],
                "reason": f"Test file directly imports '{source_file}'",
            })

    direct_candidates.sort(key=lambda c: c["file_path"])
    return direct_candidates


def find_transitive_test_dependants(
    source_file: str,
    incoming_edges: dict[str, list[dict[str, Any]]],
    direct_test_paths: set[str],
    max_depth: int = MAX_TEST_IMPACT_DEPTH,
) -> list[dict[str, Any]]:
    """Identify test files that transitively import the source file through intermediate modules.

    Uses bounded backward breadth-first search along incoming import edges.
    Guards against cycles via a visited set.

    Args:
        source_file: Normalized path of source file.
        incoming_edges: Index mapping target -> incoming edges.
        direct_test_paths: Set of test files already mapped as direct.
        max_depth: Maximum import chain depth (default: 5).

    Returns:
        List of candidate test dictionaries with mapping_status='heuristic'.
    """
    transitive_candidates: list[dict[str, Any]] = []
    seen_tests: set[str] = set(direct_test_paths)

    # Queue contains tuples of (current_node, path_to_source)
    # path_to_source starts as [source_file]
    queue: deque[tuple[str, list[str]]] = deque([(source_file, [source_file])])
    visited: set[str] = {source_file}

    while queue:
        curr, path = queue.popleft()

        if len(path) > max_depth:
            continue

        for edge in incoming_edges.get(curr, []):
            src = edge.get("source")
            if not src or not isinstance(src, str):
                continue

            full_path = [src] + path

            # If src is a test file, we found a test reachability chain
            if is_test_file(src):
                if src not in seen_tests:
                    seen_tests.add(src)
                    chain_repr = " -> ".join(full_path)
                    transitive_candidates.append({
                        "file_path": src,
                        "test_type": classify_test_type(src),
                        "mapping_status": "heuristic",
                        "evidence_type": "transitive_dependency",
                        "dependency_path": full_path,
                        "reason": f"Test file reaches '{source_file}' through intermediate dependencies ({chain_repr})",
                    })
                # Do not expand further backwards from a test file to avoid test-to-test chains
                continue

            if src not in visited and len(path) < max_depth:
                visited.add(src)
                queue.append((src, full_path))

    transitive_candidates.sort(key=lambda c: c["file_path"])
    return transitive_candidates


def find_heuristic_test_matches(
    source_file: str,
    all_test_files: list[dict[str, str]],
    already_matched_paths: set[str],
) -> list[dict[str, Any]]:
    """Match test files based on naming conventions, stems, and directory relationships.

    Args:
        source_file: Normalized repository-relative path of source file.
        all_test_files: List of all discovered test files in the repository.
        already_matched_paths: Set of test paths already identified.

    Returns:
        List of candidate test dictionaries with mapping_status='heuristic'.
    """
    heuristic_candidates: list[dict[str, Any]] = []
    source_stem = extract_stem(source_file)
    if not source_stem:
        return heuristic_candidates

    source_dir = Path(source_file).parent.as_posix()

    for item in all_test_files:
        test_path = item["file_path"]
        if test_path in already_matched_paths:
            continue

        test_stem = extract_stem(test_path)
        if not test_stem or test_stem != source_stem:
            continue

        test_dir = Path(test_path).parent.as_posix()
        test_type = item.get("test_type") or classify_test_type(test_path)

        # 1. Same directory or immediate __tests__ subdirectory
        if test_dir == source_dir or test_dir == f"{source_dir}/__tests__":
            heuristic_candidates.append({
                "file_path": test_path,
                "test_type": test_type,
                "mapping_status": "heuristic",
                "evidence_type": "directory_and_filename_match",
                "dependency_path": [],
                "reason": f"Test file in proximate directory with matching stem '{source_stem}'",
            })
            already_matched_paths.add(test_path)
        # 2. Mirror or conventional test directory
        else:
            heuristic_candidates.append({
                "file_path": test_path,
                "test_type": test_type,
                "mapping_status": "heuristic",
                "evidence_type": "filename_match",
                "dependency_path": [],
                "reason": f"Test filename stem '{test_stem}' matches source file '{source_file}'",
            })
            already_matched_paths.add(test_path)

    heuristic_candidates.sort(key=lambda c: c["file_path"])
    return heuristic_candidates


def map_tests_for_finding(
    source_file: str | None,
    incoming_edges: dict[str, list[dict[str, Any]]],
    all_discovered_tests: list[dict[str, str]],
    graph_is_available: bool = True,
    graph_is_truncated: bool = False,
) -> dict[str, Any]:
    """Perform test impact mapping for an individual source file finding.

    Args:
        source_file: Normalized repository-relative path of the flagged file.
        incoming_edges: Indexed graph incoming edges.
        all_discovered_tests: All candidate test files discovered across workspace.
        graph_is_available: Whether the dependency graph is available.
        graph_is_truncated: Whether the graph was truncated for limits.

    Returns:
        Dictionary conforming to FindingTestImpact schema.
    """
    if not source_file:
        return {
            "status": "partial",
            "mapping_complete": False,
            "candidate_tests": [],
            "summary": {
                "direct_test_count": 0,
                "heuristic_test_count": 0,
                "unknown_test_count": 0,
            },
            "notes": ["Finding does not specify a valid source file path."],
        }

    if not graph_is_available:
        # Fall back to pure heuristic naming matching when graph is unavailable
        heuristic_only = find_heuristic_test_matches(source_file, all_discovered_tests, set())
        return {
            "status": "partial",
            "mapping_complete": False,
            "candidate_tests": heuristic_only,
            "summary": {
                "direct_test_count": 0,
                "heuristic_test_count": len(heuristic_only),
                "unknown_test_count": 0,
            },
            "notes": ["Dependency graph was unavailable; results based solely on filename heuristics."],
        }

    # 1. Direct matches (graph edge: Test -> Source)
    direct_candidates = find_direct_test_dependants(source_file, incoming_edges)
    direct_paths = {c["file_path"] for c in direct_candidates}

    # 2. Transitive matches (graph chain: Test -> Intermediate -> Source)
    transitive_candidates = find_transitive_test_dependants(
        source_file, incoming_edges, direct_paths, max_depth=MAX_TEST_IMPACT_DEPTH
    )
    graph_matched_paths = direct_paths.union({c["file_path"] for c in transitive_candidates})

    # 3. Heuristic naming & directory matches for remaining tests
    heuristic_candidates = find_heuristic_test_matches(
        source_file, all_discovered_tests, set(graph_matched_paths)
    )

    all_candidates = direct_candidates + transitive_candidates + heuristic_candidates

    direct_count = len(direct_candidates)
    heuristic_count = len(transitive_candidates) + len(heuristic_candidates)

    notes: list[str] = []
    if graph_is_truncated:
        notes.append("Graph was truncated for visualization; additional transitive test links may exist.")
    notes.append("Potential test relationships reflect static imports or naming conventions, not test coverage.")

    mapping_complete = not graph_is_truncated
    status = "partial" if graph_is_truncated else "success"

    return {
        "status": status,
        "mapping_complete": mapping_complete,
        "candidate_tests": all_candidates,
        "summary": {
            "direct_test_count": direct_count,
            "heuristic_test_count": heuristic_count,
            "unknown_test_count": 0,
        },
        "notes": notes,
    }

