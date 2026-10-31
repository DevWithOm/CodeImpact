"""Unit tests for test impact mapping algorithms."""

import pytest

from backend.app.services.dependency_impact.impact_analyzer import build_graph_indexes
from backend.app.services.dependency_impact.test_mapper import (
    extract_stem,
    find_direct_test_dependants,
    find_heuristic_test_matches,
    find_transitive_test_dependants,
    map_tests_for_finding,
)


def test_extract_stem():
    assert extract_stem("src/services/payment.ts") == "payment"
    assert extract_stem("tests/payment.test.ts") == "payment"
    assert extract_stem("src/components/Button.spec.tsx") == "button"
    assert extract_stem("tests/unit/test_auth.py") == "auth"
    assert extract_stem("tests/auth_test.py") == "auth"


def test_direct_test_mapping():
    edges = [
        {"id": "tests/payment.test.ts->src/payment.ts", "source": "tests/payment.test.ts", "target": "src/payment.ts"},
        {"id": "src/app.ts->src/payment.ts", "source": "src/app.ts", "target": "src/payment.ts"},
    ]
    incoming, _ = build_graph_indexes(edges)

    candidates = find_direct_test_dependants("src/payment.ts", incoming)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["file_path"] == "tests/payment.test.ts"
    assert c["mapping_status"] == "direct"
    assert c["evidence_type"] == "static_import"
    assert c["dependency_path"] == ["tests/payment.test.ts", "src/payment.ts"]


def test_transitive_test_mapping():
    # Chain: tests/payment.test.ts -> src/index.ts -> src/processor.ts
    edges = [
        {"id": "tests/payment.test.ts->src/index.ts", "source": "tests/payment.test.ts", "target": "src/index.ts"},
        {"id": "src/index.ts->src/processor.ts", "source": "src/index.ts", "target": "src/processor.ts"},
    ]
    incoming, _ = build_graph_indexes(edges)

    # For src/processor.ts, tests/payment.test.ts is reached transitively
    direct_candidates = find_direct_test_dependants("src/processor.ts", incoming)
    assert len(direct_candidates) == 0

    transitive = find_transitive_test_dependants("src/processor.ts", incoming, direct_test_paths=set())
    assert len(transitive) == 1
    t = transitive[0]
    assert t["file_path"] == "tests/payment.test.ts"
    assert t["mapping_status"] == "heuristic"
    assert t["evidence_type"] == "transitive_dependency"
    assert t["dependency_path"] == ["tests/payment.test.ts", "src/index.ts", "src/processor.ts"]


def test_transitive_mapping_with_cycle():
    # Chain with cycle: tests/auth.test.ts -> src/user.ts <-> src/auth.ts
    edges = [
        {"id": "tests/auth.test.ts->src/user.ts", "source": "tests/auth.test.ts", "target": "src/user.ts"},
        {"id": "src/user.ts->src/auth.ts", "source": "src/user.ts", "target": "src/auth.ts"},
        {"id": "src/auth.ts->src/user.ts", "source": "src/auth.ts", "target": "src/user.ts"},
    ]
    incoming, _ = build_graph_indexes(edges)

    # Must terminate without infinite loop and find tests/auth.test.ts for src/auth.ts
    transitive = find_transitive_test_dependants("src/auth.ts", incoming, direct_test_paths=set())
    assert len(transitive) == 1
    assert transitive[0]["file_path"] == "tests/auth.test.ts"
    assert transitive[0]["mapping_status"] == "heuristic"


def test_heuristic_test_matching():
    all_tests = [
        {"file_path": "tests/payment.test.ts", "test_type": "unit_test"},
        {"file_path": "src/components/__tests__/Button.test.tsx", "test_type": "unit_test"},
        {"file_path": "tests/unrelated.test.ts", "test_type": "unit_test"},
    ]

    # Finding on src/services/payment.ts (no graph edges)
    matches = find_heuristic_test_matches("src/services/payment.ts", all_tests, already_matched_paths=set())
    assert len(matches) == 1
    assert matches[0]["file_path"] == "tests/payment.test.ts"
    assert matches[0]["mapping_status"] == "heuristic"
    assert matches[0]["evidence_type"] == "filename_match"

    # Finding on src/components/Button.tsx (proximate __tests__ match)
    matches_btn = find_heuristic_test_matches("src/components/Button.tsx", all_tests, already_matched_paths=set())
    assert len(matches_btn) == 1
    assert matches_btn[0]["file_path"] == "src/components/__tests__/Button.test.tsx"
    assert matches_btn[0]["evidence_type"] == "directory_and_filename_match"


def test_map_tests_for_finding_full_flow():
    edges = [
        {"id": "tests/app.test.ts->src/app.ts", "source": "tests/app.test.ts", "target": "src/app.ts"},
        {"id": "src/app.ts->src/utils.ts", "source": "src/app.ts", "target": "src/utils.ts"},
    ]
    incoming, _ = build_graph_indexes(edges)
    all_tests = [
        {"file_path": "tests/app.test.ts", "test_type": "unit_test"},
        {"file_path": "tests/utils.test.ts", "test_type": "unit_test"},
    ]

    # Finding on src/app.ts -> Direct test candidate
    res_app = map_tests_for_finding("src/app.ts", incoming, all_tests)
    assert res_app["status"] == "success"
    assert res_app["summary"]["direct_test_count"] == 1
    assert res_app["candidate_tests"][0]["file_path"] == "tests/app.test.ts"
    assert res_app["candidate_tests"][0]["mapping_status"] == "direct"

    # Finding on src/utils.ts -> Transitive test candidate (app.test.ts) + Heuristic (utils.test.ts)
    res_utils = map_tests_for_finding("src/utils.ts", incoming, all_tests)
    assert res_utils["status"] == "success"
    cands = {c["file_path"]: c["mapping_status"] for c in res_utils["candidate_tests"]}
    assert "tests/app.test.ts" in cands
    assert cands["tests/app.test.ts"] == "heuristic"  # transitive
    assert "tests/utils.test.ts" in cands
    assert cands["tests/utils.test.ts"] == "heuristic"  # filename stem match


def test_map_tests_for_finding_missing_path():
    res = map_tests_for_finding(None, {}, [])
    assert res["status"] == "partial"
    assert res["mapping_complete"] is False
    assert res["candidate_tests"] == []


def test_map_tests_for_finding_truncated_graph():
    res = map_tests_for_finding("src/app.ts", {}, [], graph_is_available=True, graph_is_truncated=True)
    assert res["status"] == "partial"
    assert res["mapping_complete"] is False
    assert any("truncated" in n.lower() for n in res["notes"])

