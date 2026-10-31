"""Unit tests for CodeImpact Cycle Detector."""

from __future__ import annotations

import pytest

from backend.app.services.dependency_impact.cycle_detector import (
    canonicalize_cycle_chain,
    get_cycle_members,
    normalize_cycles,
    validate_cycles,
)


def test_empty_or_none_cycles():
    """Empty or None cycle inputs return empty lists and sets."""
    assert normalize_cycles(None) == []
    assert normalize_cycles([]) == []
    assert get_cycle_members(None) == set()
    assert get_cycle_members([]) == set()
    is_valid, warnings = validate_cycles(None)
    assert is_valid is True
    assert warnings == []


def test_simple_two_node_cycle():
    """Verify normalization of a standard 2-node circular dependency."""
    raw = [["src/services/user.ts", "src/services/auth.ts"]]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 1
    # auth.ts is lexicographically smaller than user.ts, so it rotates to first position
    assert normalized[0] == ["src/services/auth.ts", "src/services/user.ts"]
    members = get_cycle_members(normalized)
    assert members == {"src/services/auth.ts", "src/services/user.ts"}


def test_multi_node_cycle_rotation():
    """Verify that multi-node cycle chains rotate canonically."""
    raw1 = [["src/b.ts", "src/c.ts", "src/a.ts"]]
    raw2 = [["src/c.ts", "src/a.ts", "src/b.ts"]]
    norm1 = normalize_cycles(raw1)
    norm2 = normalize_cycles(raw2)
    assert norm1 == norm2 == [["src/a.ts", "src/b.ts", "src/c.ts"]]


def test_duplicate_cycles_deduplicated():
    """Identical cycles with different starting nodes are deduplicated."""
    raw = [
        ["src/a.ts", "src/b.ts"],
        ["src/b.ts", "src/a.ts"],
        ["./src/a.ts", "src/b.ts"],
    ]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 1
    assert normalized[0] == ["src/a.ts", "src/b.ts"]


def test_multiple_independent_cycles():
    """Multiple disjoint cycles are both retained and sorted."""
    raw = [
        ["src/y.ts", "src/z.ts"],
        ["src/a.ts", "src/b.ts"],
    ]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 2
    assert normalized[0] == ["src/a.ts", "src/b.ts"]
    assert normalized[1] == ["src/y.ts", "src/z.ts"]


def test_node_in_multiple_cycles():
    """A node participating in more than one cycle is correctly reflected in members."""
    raw = [
        ["src/hub.ts", "src/a.ts"],
        ["src/hub.ts", "src/b.ts"],
    ]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 2
    members = get_cycle_members(normalized)
    assert members == {"src/a.ts", "src/b.ts", "src/hub.ts"}


def test_invalid_cycle_structures_filtered():
    """Single node cycles or non-list entries are safely skipped."""
    raw = [
        ["src/single.ts"],  # Only 1 unique node -> filtered
        ["src/same.ts", "src/same.ts"],  # Only 1 unique node -> filtered
        "not_a_list",
        None,
        ["src/valid1.ts", "src/valid2.ts"],
    ]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 1
    assert normalized[0] == ["src/valid1.ts", "src/valid2.ts"]


def test_path_normalization_in_cycles():
    """Windows backslashes, leading ./, and traversals in cycles are normalized."""
    raw = [
        ["src\\services\\user.ts", ".\\src\\services\\auth.ts"],
        ["src/invalid/../traversal.ts", "src/a.ts"],  # invalid traversal dropped
    ]
    normalized = normalize_cycles(raw)
    assert len(normalized) == 1
    assert normalized[0] == ["src/services/auth.ts", "src/services/user.ts"]


def test_validate_cycles_against_dependency_map():
    """Test validation detects missing edges in reported cycles."""
    cycles = [["src/a.ts", "src/b.ts"]]

    # Case A: edges exist
    dep_map_valid = {
        "src/a.ts": ["src/b.ts"],
        "src/b.ts": ["src/a.ts"],
    }
    is_valid, warnings = validate_cycles(cycles, dep_map_valid)
    assert is_valid is True
    assert warnings == []

    # Case B: missing reverse edge
    dep_map_invalid = {
        "src/a.ts": ["src/b.ts"],
        "src/b.ts": [],
    }
    is_valid, warnings = validate_cycles(cycles, dep_map_invalid)
    assert len(warnings) == 1
    assert "missing from dependency map" in warnings[0]

