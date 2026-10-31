"""Finding normalization and graph-node mapping engine for CodeImpact.

Normalizes finding file paths safely, handles schema variations (e.g. finding_id vs id),
and associates findings with dependency graph nodes without mutating input records.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from backend.app.services.dependency_impact.madge_runner import normalize_repo_relative_path

logger = logging.getLogger(__name__)

# Canonical Mapping Statuses
MAPPING_STATUS_MAPPED = "mapped"
MAPPING_STATUS_UNMAPPED = "unmapped"
MAPPING_STATUS_INVALID_PATH = "invalid_path"
MAPPING_STATUS_MISSING_FILE_PATH = "missing_file_path"


def validate_and_normalize_path(raw_path: Any) -> tuple[str | None, str]:
    """Validate and normalize a file path from a finding.

    Args:
        raw_path: File path as provided in finding dictionary or schema.

    Returns:
        tuple (normalized_path, status) where:
        - normalized_path is the POSIX repo-relative path if valid, or None.
        - status is one of MAPPING_STATUS_MISSING_FILE_PATH, MAPPING_STATUS_INVALID_PATH,
          or 'valid'.
    """
    if raw_path is None:
        return None, MAPPING_STATUS_MISSING_FILE_PATH

    if not isinstance(raw_path, str):
        return None, MAPPING_STATUS_INVALID_PATH

    cleaned = raw_path.strip()
    if not cleaned:
        return None, MAPPING_STATUS_MISSING_FILE_PATH

    # Normalize using Phase 2 runner utility
    normalized = normalize_repo_relative_path(cleaned)
    if not normalized:
        # If raw_path was non-empty but normalize_repo_relative_path returned None,
        # it was either an absolute path (C:\..., /...) or a traversal attempt (../...)
        return None, MAPPING_STATUS_INVALID_PATH

    return normalized, "valid"


def extract_finding_adapter(finding: dict[str, Any]) -> dict[str, Any]:
    """Extract and adapt finding fields to a canonical interface while preserving all original keys.

    Handles variations such as:
    - finding_id vs id
    - category vs type vs finding_type
    - description vs message

    Args:
        finding: Raw finding dictionary.

    Returns:
        Deep copy of dictionary with canonical aliases populated without mutating input.
    """
    adapted = copy.deepcopy(finding)

    # 1. Finding ID
    finding_id = adapted.get("finding_id") or adapted.get("id")
    if finding_id is not None:
        adapted["finding_id"] = str(finding_id)
        if "id" not in adapted:
            adapted["id"] = str(finding_id)

    # 2. Category / Type
    category = adapted.get("category") or adapted.get("type") or adapted.get("finding_type")
    if category is not None:
        adapted["category"] = str(category)
        if "type" not in adapted:
            adapted["type"] = str(category)

    # 3. Description / Message
    description = adapted.get("description") or adapted.get("message")
    if description is not None:
        adapted["description"] = str(description)
        if "message" not in adapted:
            adapted["message"] = str(description)

    return adapted


def map_finding_to_node(
    finding: dict[str, Any],
    node_ids: set[str],
) -> tuple[dict[str, Any], str, str | None, str | None]:
    """Map a single finding to a graph node.

    Args:
        finding: Raw finding dictionary.
        node_ids: Set of canonical node IDs existing in the dependency graph.

    Returns:
        tuple (adapted_finding, mapping_status, matched_node_id, unmapped_reason)
    """
    adapted = extract_finding_adapter(finding)
    raw_path = adapted.get("file_path")

    normalized_path, path_status = validate_and_normalize_path(raw_path)

    if path_status == MAPPING_STATUS_MISSING_FILE_PATH:
        adapted["file_path"] = None
        return (
            adapted,
            MAPPING_STATUS_MISSING_FILE_PATH,
            None,
            "Finding does not specify a valid file_path",
        )

    if path_status == MAPPING_STATUS_INVALID_PATH:
        return (
            adapted,
            MAPPING_STATUS_INVALID_PATH,
            None,
            f"Finding specifies an invalid or unsafe file path: '{raw_path}'",
        )

    # Update adapted finding with normalized POSIX repo-relative path
    adapted["file_path"] = normalized_path

    if normalized_path in node_ids:
        return adapted, MAPPING_STATUS_MAPPED, normalized_path, None

    return (
        adapted,
        MAPPING_STATUS_UNMAPPED,
        None,
        f"File '{normalized_path}' is not present in the dependency graph",
    )


def map_findings_to_nodes(
    findings: list[dict[str, Any]] | None,
    graph_nodes: list[dict[str, Any]] | set[str] | None,
) -> list[tuple[dict[str, Any], str, str | None, str | None]]:
    """Map a collection of findings to a dependency graph's nodes.

    Handles multiple findings on the same file independently without deduplication
    or merging.

    Args:
        findings: List of finding dictionaries.
        graph_nodes: List of node dictionaries or set of node ID strings.

    Returns:
        List of tuples: (adapted_finding, mapping_status, matched_node_id, reason)
    """
    if not findings:
        return []

    # Build node_id lookup set
    node_ids: set[str] = set()
    if graph_nodes:
        if isinstance(graph_nodes, set):
            node_ids = graph_nodes
        elif isinstance(graph_nodes, list):
            for item in graph_nodes:
                if isinstance(item, str):
                    node_ids.add(item)
                elif isinstance(item, dict):
                    nid = item.get("id") or item.get("file_path")
                    if nid and isinstance(nid, str):
                        node_ids.add(nid)

    mapped_results: list[tuple[dict[str, Any], str, str | None, str | None]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        mapped_results.append(map_finding_to_node(f, node_ids))

    return mapped_results

