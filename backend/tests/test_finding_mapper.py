"""Unit tests for finding path normalization and graph node mapping."""

import pytest

from backend.app.services.dependency_impact.finding_mapper import (
    MAPPING_STATUS_INVALID_PATH,
    MAPPING_STATUS_MAPPED,
    MAPPING_STATUS_MISSING_FILE_PATH,
    MAPPING_STATUS_UNMAPPED,
    extract_finding_adapter,
    map_finding_to_node,
    map_findings_to_nodes,
    validate_and_normalize_path,
)


def test_validate_and_normalize_path_exact():
    norm, status = validate_and_normalize_path("src/utils/helpers.ts")
    assert norm == "src/utils/helpers.ts"
    assert status == "valid"


def test_validate_and_normalize_path_windows_separators():
    norm, status = validate_and_normalize_path(r"src\utils\helpers.ts")
    assert norm == "src/utils/helpers.ts"
    assert status == "valid"


def test_validate_and_normalize_path_redundant_dot_slash():
    norm, status = validate_and_normalize_path("./src/utils/helpers.ts")
    assert norm == "src/utils/helpers.ts"
    assert status == "valid"


def test_validate_and_normalize_path_missing_or_none():
    norm1, status1 = validate_and_normalize_path(None)
    assert norm1 is None
    assert status1 == MAPPING_STATUS_MISSING_FILE_PATH

    norm2, status2 = validate_and_normalize_path("")
    assert norm2 is None
    assert status2 == MAPPING_STATUS_MISSING_FILE_PATH

    norm3, status3 = validate_and_normalize_path("   ")
    assert norm3 is None
    assert status3 == MAPPING_STATUS_MISSING_FILE_PATH


def test_validate_and_normalize_path_absolute_rejection():
    # Windows drive path
    norm1, status1 = validate_and_normalize_path("C:\\DeadCode\\src\\app.ts")
    assert norm1 is None
    assert status1 == MAPPING_STATUS_INVALID_PATH

    # Unix root path
    norm2, status2 = validate_and_normalize_path("/etc/passwd")
    assert norm2 is None
    assert status2 == MAPPING_STATUS_INVALID_PATH


def test_validate_and_normalize_path_traversal_rejection():
    norm, status = validate_and_normalize_path("../secret.ts")
    assert norm is None
    assert status == MAPPING_STATUS_INVALID_PATH

    norm2, status2 = validate_and_normalize_path("src/../../secret.ts")
    assert norm2 is None
    assert status2 == MAPPING_STATUS_INVALID_PATH


def test_extract_finding_adapter_canonical_fields():
    # OM_2 canonical structure
    raw = {
        "finding_id": "f_100",
        "category": "unused_export",
        "file_path": "src/app.ts",
        "description": "Unused export found.",
    }
    adapted = extract_finding_adapter(raw)
    assert adapted["finding_id"] == "f_100"
    assert adapted["id"] == "f_100"
    assert adapted["category"] == "unused_export"
    assert adapted["type"] == "unused_export"
    assert adapted["description"] == "Unused export found."
    assert adapted["message"] == "Unused export found."


def test_extract_finding_adapter_alternate_aliases():
    # Alternate schema with id, type, message
    raw = {
        "id": "FIND-001",
        "type": "duplicate_code",
        "file_path": "src/utils.ts",
        "message": "Duplicate block.",
    }
    adapted = extract_finding_adapter(raw)
    assert adapted["finding_id"] == "FIND-001"
    assert adapted["id"] == "FIND-001"
    assert adapted["category"] == "duplicate_code"
    assert adapted["type"] == "duplicate_code"
    assert adapted["description"] == "Duplicate block."
    assert adapted["message"] == "Duplicate block."


def test_map_finding_to_node_mapped_success():
    finding = {"finding_id": "f_01", "file_path": r"src\components\Button.tsx"}
    nodes = {"src/components/Button.tsx", "src/main.tsx"}

    adapted, status, matched_id, reason = map_finding_to_node(finding, nodes)
    assert status == MAPPING_STATUS_MAPPED
    assert matched_id == "src/components/Button.tsx"
    assert adapted["file_path"] == "src/components/Button.tsx"
    assert reason is None


def test_map_finding_to_node_unmapped():
    finding = {"finding_id": "f_02", "file_path": "src/missing.ts"}
    nodes = {"src/app.ts", "src/main.ts"}

    adapted, status, matched_id, reason = map_finding_to_node(finding, nodes)
    assert status == MAPPING_STATUS_UNMAPPED
    assert matched_id is None
    assert "not present in the dependency graph" in reason


def test_map_finding_to_node_missing_path():
    finding = {"finding_id": "f_03", "category": "unused_dependency"}
    nodes = {"src/app.ts"}

    adapted, status, matched_id, reason = map_finding_to_node(finding, nodes)
    assert status == MAPPING_STATUS_MISSING_FILE_PATH
    assert matched_id is None
    assert "does not specify a valid file_path" in reason


def test_map_finding_to_node_invalid_path():
    finding = {"finding_id": "f_04", "file_path": "C:\\root\\file.ts"}
    nodes = {"src/app.ts"}

    adapted, status, matched_id, reason = map_finding_to_node(finding, nodes)
    assert status == MAPPING_STATUS_INVALID_PATH
    assert matched_id is None
    assert "invalid or unsafe file path" in reason


def test_map_findings_to_nodes_multiple_findings_same_file():
    findings = [
        {"finding_id": "f_1", "file_path": "src/utils.ts", "category": "unused_export"},
        {"finding_id": "f_2", "file_path": "src/utils.ts", "category": "duplicate_code"},
    ]
    nodes = {"src/utils.ts", "src/main.ts"}

    results = map_findings_to_nodes(findings, nodes)
    assert len(results) == 2
    assert results[0][1] == MAPPING_STATUS_MAPPED
    assert results[0][2] == "src/utils.ts"
    assert results[0][0]["finding_id"] == "f_1"

    assert results[1][1] == MAPPING_STATUS_MAPPED
    assert results[1][2] == "src/utils.ts"
    assert results[1][0]["finding_id"] == "f_2"


def test_map_findings_to_nodes_empty_inputs():
    assert map_findings_to_nodes([], {"src/main.ts"}) == []
    assert map_findings_to_nodes(None, {"src/main.ts"}) == []

    # Non-empty findings with empty nodes -> all unmapped
    findings = [{"finding_id": "f_1", "file_path": "src/main.ts"}]
    res = map_findings_to_nodes(findings, set())
    assert len(res) == 1
    assert res[0][1] == MAPPING_STATUS_UNMAPPED


def test_map_findings_to_nodes_accepts_node_dicts():
    findings = [{"finding_id": "f_1", "file_path": "src/main.ts"}]
    node_dicts = [{"id": "src/main.ts", "label": "main.ts"}]

    res = map_findings_to_nodes(findings, node_dicts)
    assert len(res) == 1
    assert res[0][1] == MAPPING_STATUS_MAPPED
    assert res[0][2] == "src/main.ts"

