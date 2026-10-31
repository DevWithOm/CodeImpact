"""SAMAR_3: Dependency & Impact Engine package.

Exposes Madge dependency extraction runner, graph builder, cycle detector,
impact analyzer, finding mapper, test mapper, and review risk engine.
"""

from backend.app.schemas.impact import (
    DirectDependant,
    EnrichedFinding,
    FindingImpactSummary,
    ImpactEvidence,
)
from backend.app.services.dependency_impact.cycle_detector import (
    canonicalize_cycle_chain,
    get_cycle_members,
    normalize_cycles,
    validate_cycles,
)
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
from backend.app.services.dependency_impact.graph_builder import (
    DEFAULT_MAX_EDGES,
    DEFAULT_MAX_NODES,
    build_dependency_graph,
    create_graph_response,
    extract_finding_counts_by_file,
    validate_graph_integrity,
)
from backend.app.services.dependency_impact.impact_analyzer import (
    EVIDENCE_TYPE_STATIC_IMPORT,
    IMPACT_STATUS_PARTIAL,
    IMPACT_STATUS_SUCCESS,
    IMPACT_STATUS_UNAVAILABLE,
    analyze_impact,
    build_graph_indexes,
    enrich_finding,
    extract_direct_dependants,
    extract_direct_dependencies,
)
from backend.app.services.dependency_impact.madge_runner import (
    ERR_MADGE_EXECUTION_FAILED,
    ERR_MADGE_INVALID_JSON,
    ERR_MADGE_NOT_FOUND,
    ERR_MADGE_OUTPUT_LIMIT_EXCEEDED,
    ERR_MADGE_PARTIAL_OUTPUT,
    ERR_MADGE_TIMEOUT,
    ERR_REPOSITORY_NOT_FOUND,
    ERR_REPOSITORY_PATH_INVALID,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    find_madge_entrypoint,
    find_madge_executable,
    find_node_executable,
    get_circular_dependencies,
    get_dependency_map,
    get_madge_version,
    normalize_repo_relative_path,
    resolve_madge_command,
    run_madge,
    run_subprocess_bounded,
    sanitize_message,
)

__all__ = [
    # Madge Runner
    "run_madge",
    "get_dependency_map",
    "get_circular_dependencies",
    "find_madge_executable",
    "find_node_executable",
    "find_madge_entrypoint",
    "resolve_madge_command",
    "run_subprocess_bounded",
    "get_madge_version",
    "normalize_repo_relative_path",
    "sanitize_message",
    # Graph Builder
    "build_dependency_graph",
    "create_graph_response",
    "validate_graph_integrity",
    "extract_finding_counts_by_file",
    "DEFAULT_MAX_NODES",
    "DEFAULT_MAX_EDGES",
    # Cycle Detector
    "normalize_cycles",
    "get_cycle_members",
    "validate_cycles",
    "canonicalize_cycle_chain",
    # Finding Mapper
    "validate_and_normalize_path",
    "extract_finding_adapter",
    "map_finding_to_node",
    "map_findings_to_nodes",
    "MAPPING_STATUS_MAPPED",
    "MAPPING_STATUS_UNMAPPED",
    "MAPPING_STATUS_INVALID_PATH",
    "MAPPING_STATUS_MISSING_FILE_PATH",
    # Impact Analyzer
    "analyze_impact",
    "build_graph_indexes",
    "extract_direct_dependants",
    "extract_direct_dependencies",
    "enrich_finding",
    "IMPACT_STATUS_SUCCESS",
    "IMPACT_STATUS_PARTIAL",
    "IMPACT_STATUS_UNAVAILABLE",
    "EVIDENCE_TYPE_STATIC_IMPORT",
    # Impact Schemas
    "EnrichedFinding",
    "DirectDependant",
    "FindingImpactSummary",
    "ImpactEvidence",
    # Canonical Statuses & Error Codes
    "STATUS_SUCCESS",
    "STATUS_PARTIAL",
    "STATUS_FAILED",
    "STATUS_UNAVAILABLE",
    "ERR_MADGE_NOT_FOUND",
    "ERR_MADGE_EXECUTION_FAILED",
    "ERR_MADGE_TIMEOUT",
    "ERR_MADGE_INVALID_JSON",
    "ERR_MADGE_OUTPUT_LIMIT_EXCEEDED",
    "ERR_REPOSITORY_PATH_INVALID",
    "ERR_REPOSITORY_NOT_FOUND",
    "ERR_MADGE_PARTIAL_OUTPUT",
]
