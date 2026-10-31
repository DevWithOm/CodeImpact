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
from backend.app.schemas.risk import (
    FindingRiskResult,
    RiskAnalysisResult,
    RiskAssessment,
    RiskFactorBreakdown,
    RiskSummary,
)
from backend.app.schemas.test_impact import (
    EntryPointEvidence,
    FindingTestImpact,
    FrameworkEvidence,
    TestCandidate,
    TestImpactAnalysisResult,
    TestImpactSummary,
)
from backend.app.services.dependency_impact.cycle_detector import (
    canonicalize_cycle_chain,
    get_cycle_members,
    normalize_cycles,
    validate_cycles,
)
from backend.app.services.dependency_impact.entry_point_detector import (
    detect_entry_points,
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
from backend.app.services.dependency_impact.test_discovery import (
    TEST_TYPE_CONFIG,
    TEST_TYPE_E2E,
    TEST_TYPE_INTEGRATION,
    TEST_TYPE_UNIT,
    TEST_TYPE_UNKNOWN,
    classify_test_type,
    discover_test_files,
    discover_test_files_from_nodes,
    is_test_file,
    scan_repository_for_tests,
)
from backend.app.services.dependency_impact.test_framework_detector import (
    detect_test_frameworks,
)
from backend.app.services.dependency_impact.test_impact_analyzer import (
    analyze_test_impact,
)
from backend.app.services.dependency_impact.test_mapper import (
    find_direct_test_dependants,
    find_heuristic_test_matches,
    find_transitive_test_dependants,
    map_tests_for_finding,
)
from backend.app.services.dependency_impact.risk_scorer import (
    RISK_LEVEL_HIGHER,
    RISK_LEVEL_LOWER,
    RISK_LEVEL_MEDIUM,
    RISK_LEVEL_UNKNOWN,
    calculate_risk_score,
    classify_risk,
)
from backend.app.services.dependency_impact.risk_explainer import (
    generate_mitigating_observations,
    generate_positive_factors,
    generate_recommendation,
    generate_uncertainties,
)
from backend.app.services.dependency_impact.risk_analyzer import (
    analyze_review_risk,
    compute_completeness,
    compute_confidence,
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
    # Test Discovery & Classification
    "is_test_file",
    "classify_test_type",
    "discover_test_files",
    "discover_test_files_from_nodes",
    "scan_repository_for_tests",
    "TEST_TYPE_UNIT",
    "TEST_TYPE_INTEGRATION",
    "TEST_TYPE_E2E",
    "TEST_TYPE_CONFIG",
    "TEST_TYPE_UNKNOWN",
    # Framework & Entry-Point Detection
    "detect_test_frameworks",
    "detect_entry_points",
    # Test Mapper & Analyzer
    "map_tests_for_finding",
    "find_direct_test_dependants",
    "find_transitive_test_dependants",
    "find_heuristic_test_matches",
    "analyze_test_impact",
    # Impact Schemas
    "EnrichedFinding",
    "DirectDependant",
    "FindingImpactSummary",
    "ImpactEvidence",
    # Test Impact Schemas
    "TestCandidate",
    "TestImpactSummary",
    "FindingTestImpact",
    "FrameworkEvidence",
    "EntryPointEvidence",
    "TestImpactAnalysisResult",
    # Review-Risk Schemas
    "RiskFactorBreakdown",
    "RiskAssessment",
    "FindingRiskResult",
    "RiskSummary",
    "RiskAnalysisResult",
    # Review-Risk Engine
    "analyze_review_risk",
    "calculate_risk_score",
    "classify_risk",
    "compute_confidence",
    "compute_completeness",
    "generate_positive_factors",
    "generate_mitigating_observations",
    "generate_uncertainties",
    "generate_recommendation",
    "RISK_LEVEL_HIGHER",
    "RISK_LEVEL_MEDIUM",
    "RISK_LEVEL_LOWER",
    "RISK_LEVEL_UNKNOWN",
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
