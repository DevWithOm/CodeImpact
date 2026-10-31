"""Circular dependency detection and cycle normalization for CodeImpact.

Normalizes circular dependency chains from Madge, identifies cycle-member nodes,
and validates topological cycle consistency with the dependency graph.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.services.dependency_impact.madge_runner import normalize_repo_relative_path

logger = logging.getLogger(__name__)


def canonicalize_cycle_chain(chain: list[str]) -> list[str]:
    """Rotate a directed cycle chain so the lexicographically smallest element is first.

    This ensures that rotationally equivalent cycle representations
    (e.g., ['b.ts', 'c.ts', 'a.ts'] and ['a.ts', 'b.ts', 'c.ts']) produce
    an identical canonical list.

    Args:
        chain: Directed cycle chain of file paths.

    Returns:
        Canonicalized cycle list.
    """
    if not chain or len(chain) <= 1:
        return list(chain)

    # Find index of minimum element
    min_idx = min(range(len(chain)), key=lambda i: chain[i])
    if min_idx == 0:
        return list(chain)

    return chain[min_idx:] + chain[:min_idx]


def normalize_cycles(raw_cycles: list[Any] | None) -> list[list[str]]:
    """Validate, normalize paths, deduplicate, and sort circular dependency chains.

    Args:
        raw_cycles: Raw cycle list from Madge or external detection.

    Returns:
        Deterministic list of canonicalized cycle path lists.
    """
    if not raw_cycles or not isinstance(raw_cycles, list):
        return []

    normalized_set: set[tuple[str, ...]] = set()

    for item in raw_cycles:
        if not isinstance(item, (list, tuple)):
            continue

        clean_chain: list[str] = []
        for p in item:
            if not isinstance(p, str):
                continue
            norm_p = normalize_repo_relative_path(p)
            if norm_p:
                clean_chain.append(norm_p)

        # A valid circular dependency must involve at least 2 files
        # Check unique members in chain
        unique_members = set(clean_chain)
        if len(unique_members) < 2:
            continue

        # If the last element is identical to the first (e.g. ['a', 'b', 'a']), strip trailing duplicate
        if clean_chain and clean_chain[0] == clean_chain[-1]:
            clean_chain = clean_chain[:-1]

        canonical = canonicalize_cycle_chain(clean_chain)
        if len(canonical) >= 2:
            normalized_set.add(tuple(canonical))

    # Sort deterministically
    sorted_cycles = sorted(list(normalized_set))
    return [list(c) for c in sorted_cycles]


def get_cycle_members(cycles: list[list[str]] | None) -> set[str]:
    """Extract the unique set of file paths that participate in at least one cycle.

    Args:
        cycles: Normalized list of cycle chains.

    Returns:
        Set of repository-relative file paths.
    """
    if not cycles:
        return set()

    members: set[str] = set()
    for cycle in cycles:
        for f in cycle:
            if f:
                members.add(f)

    return members


def validate_cycles(
    cycles: list[list[str]] | None,
    dependency_map: dict[str, list[str]] | None = None,
) -> tuple[bool, list[str]]:
    """Validate that cycles are structurally sound and consistent with dependency map.

    Args:
        cycles: Normalized list of cycles.
        dependency_map: Optional complete repository dependency mapping.

    Returns:
        Tuple of (is_valid, warnings_list).
    """
    if not cycles:
        return True, []

    warnings: list[str] = []
    is_valid = True

    for cycle in cycles:
        if len(cycle) < 2:
            warnings.append(f"Cycle has fewer than 2 elements: {cycle}")
            is_valid = False
            continue

        if len(set(cycle)) != len(cycle):
            warnings.append(f"Cycle contains internal duplicates: {cycle}")

        if dependency_map is not None:
            # Verify each step source -> target exists in dependency_map
            n = len(cycle)
            for i in range(n):
                src = cycle[i]
                tgt = cycle[(i + 1) % n]
                deps = dependency_map.get(src, [])
                if tgt not in deps:
                    warnings.append(
                        f"Reported cycle step '{src}' -> '{tgt}' is missing from dependency map."
                    )

    return is_valid, warnings

