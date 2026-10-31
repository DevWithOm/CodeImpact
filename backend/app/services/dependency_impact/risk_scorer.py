"""Deterministic Review-Risk Scorer for CodeImpact.

Calculates bounded (0-100) numerical risk scores based on observed dependency exposure,
cycle membership, entry-point indicators, test impact relationships, finding properties,
and structural characteristics.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.schemas.risk import RiskFactorBreakdown
from backend.app.services.dependency_impact.finding_mapper import (
    MAPPING_STATUS_INVALID_PATH,
    MAPPING_STATUS_MAPPED,
    MAPPING_STATUS_MISSING_FILE_PATH,
    MAPPING_STATUS_UNMAPPED,
)

logger = logging.getLogger(__name__)

# Review risk categories
RISK_LEVEL_LOWER = "lower"
RISK_LEVEL_MEDIUM = "medium"
RISK_LEVEL_HIGHER = "higher"
RISK_LEVEL_UNKNOWN = "unknown"

# Thresholds
LOWER_THRESHOLD = 30.0
MEDIUM_THRESHOLD = 60.0

# Factor maximum scores
MAX_F1_DEPENDENCY = 25.0
MAX_F2_CYCLE = 15.0
MAX_F3_ENTRY_POINT = 20.0
MAX_F4_TEST_IMPACT = 15.0
MAX_F5_FINDING_EVIDENCE = 15.0
MAX_F6_STRUCTURAL = 10.0

CORE_ARCH_DIRS = ("services/", "core/", "api/", "config/", "shared/", "lib/")


def _extract_module_dir(path: str) -> str:
    """Extract canonical architectural module directory from a path."""
    from pathlib import Path
    parent = Path(path).parent.as_posix()
    return parent


def classify_risk(score: float | None, is_valid_assessment: bool = True) -> str:
    """Classify numeric risk score into categorical review risk.

    Args:
        score: Deterministic score between 0 and 100, or None.
        is_valid_assessment: Whether the finding and graph allow a valid assessment.

    Returns:
        One of 'lower', 'medium', 'higher', or 'unknown'.
    """
    if not is_valid_assessment or score is None:
        return RISK_LEVEL_UNKNOWN

    if score < LOWER_THRESHOLD:
        return RISK_LEVEL_LOWER
    elif score < MEDIUM_THRESHOLD:
        return RISK_LEVEL_MEDIUM
    else:
        return RISK_LEVEL_HIGHER


def score_dependency_exposure(
    finding: dict[str, Any],
    graph_is_available: bool = True,
) -> RiskFactorBreakdown:
    """F1: Calculate dependency exposure (max 25 points)."""
    mapping_status = finding.get("mapping_status", MAPPING_STATUS_UNMAPPED)
    if not graph_is_available:
        return RiskFactorBreakdown(
            factor="dependency_exposure",
            score=0.0,
            maximum_score=MAX_F1_DEPENDENCY,
            observed_value=0,
            status="unavailable",
            reason="Dependency graph is unavailable; dependency exposure cannot be evaluated.",
            evidence=[],
        )

    if mapping_status != MAPPING_STATUS_MAPPED:
        return RiskFactorBreakdown(
            factor="dependency_exposure",
            score=0.0,
            maximum_score=MAX_F1_DEPENDENCY,
            observed_value=0,
            status="unmapped",
            reason="Finding could not be mapped to dependency graph.",
            evidence=[],
        )

    direct_dependants = finding.get("direct_dependants") or []
    count = len(direct_dependants)
    evidence_paths = [
        d.get("file_path", "") if isinstance(d, dict) else getattr(d, "file_path", "")
        for d in direct_dependants
    ]
    evidence_paths = [p for p in evidence_paths if p]

    # Base: 5 points per direct dependant up to 20
    base_score = min(float(count * 5), 20.0)

    # Breadth bonus: +5 if count >= 5 or spans >= 2 distinct top-level directories
    top_dirs = {_extract_module_dir(p) for p in evidence_paths if "/" in p}
    breadth_bonus = 0.0
    if count >= 5 or len(top_dirs) >= 2:
        breadth_bonus = 5.0

    score = min(base_score + breadth_bonus, MAX_F1_DEPENDENCY)

    if count == 0:
        reason = "No direct dependants import this file."
    elif count == 1:
        reason = f"1 direct dependant imports this file ({evidence_paths[0]})."
    else:
        reason = f"{count} direct dependants import this file across {max(1, len(top_dirs))} directory structures."

    return RiskFactorBreakdown(
        factor="dependency_exposure",
        score=score,
        maximum_score=MAX_F1_DEPENDENCY,
        observed_value=count,
        status="evaluated",
        reason=reason,
        evidence=evidence_paths,
    )


def score_cycle_exposure(
    finding: dict[str, Any],
    graph_is_available: bool = True,
) -> RiskFactorBreakdown:
    """F2: Calculate cycle exposure (max 15 points)."""
    mapping_status = finding.get("mapping_status", MAPPING_STATUS_UNMAPPED)
    if not graph_is_available or mapping_status != MAPPING_STATUS_MAPPED:
        return RiskFactorBreakdown(
            factor="cycle_exposure",
            score=0.0,
            maximum_score=MAX_F2_CYCLE,
            observed_value=None,
            status="unavailable" if not graph_is_available else "unmapped",
            reason="Cycle exposure cannot be evaluated because graph is unavailable or unmapped.",
            evidence=[],
        )

    is_cycle_member = bool(finding.get("cycle_member", False))
    self_loop = bool(finding.get("self_dependency_detected", False))
    cycles = finding.get("cycles") or []

    # Check for multi-file cycle: cycle chain with >= 2 distinct nodes
    has_multi_file_cycle = False
    multi_file_chains: list[list[str]] = []
    for chain in cycles:
        if isinstance(chain, list) and len(set(chain)) >= 2:
            has_multi_file_cycle = True
            multi_file_chains.append(chain)

    if has_multi_file_cycle or (is_cycle_member and not self_loop):
        score = MAX_F2_CYCLE
        observed = "multi_file_cycle"
        reason = f"Module is a member of {max(1, len(multi_file_chains))} multi-file dependency cycle(s)."
        evidence = multi_file_chains if multi_file_chains else cycles
    elif self_loop:
        score = 4.0
        observed = "self_loop_only"
        reason = "Module imports itself (self-loop), but no multi-file circular dependency detected."
        evidence = [[finding.get("file_path", ""), finding.get("file_path", "")]]
    else:
        score = 0.0
        observed = "no_cycle"
        reason = "No circular dependencies detected for this module."
        evidence = []

    return RiskFactorBreakdown(
        factor="cycle_exposure",
        score=score,
        maximum_score=MAX_F2_CYCLE,
        observed_value=observed,
        status="evaluated",
        reason=reason,
        evidence=evidence,
    )


def score_entry_point_exposure(
    finding: dict[str, Any],
    entry_points: list[dict[str, Any]] | None = None,
) -> RiskFactorBreakdown:
    """F3: Calculate entry-point exposure (max 20 points)."""
    file_path = finding.get("file_path") or ""
    if not file_path:
        return RiskFactorBreakdown(
            factor="entry_point_exposure",
            score=0.0,
            maximum_score=MAX_F3_ENTRY_POINT,
            observed_value=None,
            status="unmapped",
            reason="Missing file path; entry point exposure cannot be evaluated.",
            evidence=[],
        )

    # Check against detected entry points
    matched_ep: dict[str, Any] | None = None
    if entry_points:
        for ep in entry_points:
            ep_path = ep.get("file_path") if isinstance(ep, dict) else getattr(ep, "file_path", "")
            if ep_path == file_path:
                matched_ep = ep if isinstance(ep, dict) else ep.model_dump()
                break

    score = 0.0
    evidence: list[Any] = []
    observed = "not_entry_point"
    reason = "File was not identified as an application or module entry point."

    if matched_ep:
        ep_type = matched_ep.get("entry_point_type", "application_entry")
        evidence = matched_ep.get("evidence", [])
        if ep_type in ("package_main", "cli_bin"):
            score = 20.0
            observed = f"strong_entry_point_{ep_type}"
            reason = f"Module is a strongly supported application entry point ({ep_type})."
        elif ep_type == "application_entry":
            score = 12.0
            observed = "standard_application_entry"
            reason = "Module matches canonical application entry point structure."
        else:
            score = 5.0
            observed = f"heuristic_{ep_type}"
            reason = f"Module exhibits entry point characteristics ({ep_type})."
    else:
        # Fallback heuristic on standard root entry patterns
        norm = file_path.lower()
        if norm in ("src/index.ts", "src/index.js", "src/main.ts", "src/main.js", "src/app.tsx", "src/app.ts", "server.ts", "index.ts", "main.ts"):
            score = 12.0
            observed = "canonical_entry_filename"
            reason = "File matches standard top-level entry point naming convention."
            evidence = [{"file_path": file_path, "heuristic": "canonical_name"}]

    return RiskFactorBreakdown(
        factor="entry_point_exposure",
        score=score,
        maximum_score=MAX_F3_ENTRY_POINT,
        observed_value=observed,
        status="evaluated",
        reason=reason,
        evidence=evidence,
    )


def score_test_impact_evidence(
    finding: dict[str, Any],
) -> RiskFactorBreakdown:
    """F4: Calculate test-impact evidence (max 15 points).

    IMPORTANT: The absence of tests contributes 0 points. It NEVER reduces the score.
    """
    test_impact = finding.get("test_impact")
    if not test_impact or not isinstance(test_impact, dict):
        return RiskFactorBreakdown(
            factor="test_impact_evidence",
            score=0.0,
            maximum_score=MAX_F4_TEST_IMPACT,
            observed_value="not_evaluated",
            status="not_applicable",
            reason="Test impact was not evaluated; no test candidates identified.",
            evidence=[],
        )

    summary = test_impact.get("summary") or {}
    candidates = test_impact.get("candidate_tests") or []
    direct_count = summary.get("direct_test_count", 0)
    heuristic_count = summary.get("heuristic_test_count", 0)

    # Check for direct test candidate
    has_direct = direct_count > 0 or any(
        (c.get("mapping_status") == "direct" if isinstance(c, dict) else getattr(c, "mapping_status", "") == "direct")
        for c in candidates
    )
    # Check for transitive graph-backed candidate
    has_transitive = any(
        (c.get("evidence_type") == "transitive_dependency" if isinstance(c, dict) else getattr(c, "evidence_type", "") == "transitive_dependency")
        for c in candidates
    )

    evidence_files = [
        c.get("file_path", "") if isinstance(c, dict) else getattr(c, "file_path", "")
        for c in candidates
    ]
    evidence_files = [f for f in evidence_files if f]

    if has_direct:
        score = 15.0
        observed = "direct_test_candidate"
        reason = f"{max(1, direct_count)} candidate test(s) directly import this source module."
    elif has_transitive:
        score = 10.0
        observed = "transitive_test_candidate"
        reason = "Candidate test(s) depend on this module via bounded dependency chains."
    elif candidates or heuristic_count > 0:
        score = 6.0
        observed = "heuristic_test_candidate"
        reason = f"{len(candidates)} candidate test(s) identified through name/directory heuristics."
    else:
        score = 0.0
        observed = "no_tests_identified"
        reason = "No candidate test files were identified."

    return RiskFactorBreakdown(
        factor="test_impact_evidence",
        score=score,
        maximum_score=MAX_F4_TEST_IMPACT,
        observed_value=observed,
        status="evaluated",
        reason=reason,
        evidence=evidence_files,
    )


def score_finding_evidence(
    finding: dict[str, Any],
) -> RiskFactorBreakdown:
    """F5: Calculate finding evidence and uncertainty (max 15 points)."""
    category = finding.get("category", "")
    evidence_class = finding.get("evidence_class", "")

    score = 0.0
    reasons: list[str] = []

    if category == "unused_export":
        score += 10.0
        reasons.append("Exported symbol carries external consumer and dynamic import risk.")
    elif category == "duplicate_code":
        score += 8.0
        reasons.append("Duplicate code refactoring involves architectural reconciliation.")
    elif category == "unused_file":
        score += 5.0
        reasons.append("Whole file reported unused by static analysis.")
    else:
        score += 5.0
        reasons.append(f"Finding category '{category}' observed.")

    if evidence_class == "inconclusive":
        score += 5.0
        reasons.append("Static scan evidence is inconclusive; heightened review uncertainty.")

    score = min(score, MAX_F5_FINDING_EVIDENCE)

    return RiskFactorBreakdown(
        factor="finding_evidence_uncertainty",
        score=score,
        maximum_score=MAX_F5_FINDING_EVIDENCE,
        observed_value={"category": category, "evidence_class": evidence_class},
        status="evaluated",
        reason="; ".join(reasons),
        evidence=finding.get("evidence") or [],
    )


def score_structural_exposure(
    finding: dict[str, Any],
) -> RiskFactorBreakdown:
    """F6: Calculate special structural exposure (max 10 points)."""
    file_path = finding.get("file_path", "")
    direct_dependencies = finding.get("direct_dependencies") or []
    out_degree = len(direct_dependencies)

    score = 0.0
    reasons: list[str] = []

    if out_degree >= 5:
        score += 5.0
        reasons.append(f"High outbound coupling ({out_degree} direct dependencies).")

    dir_parts = set(file_path.split("/")[:-1])
    is_core_dir = any(
        file_path.startswith(d) or d.rstrip("/") in dir_parts
        for d in CORE_ARCH_DIRS
    )
    if is_core_dir:
        score += 5.0
        reasons.append("Module resides in core architectural directory.")

    score = min(score, MAX_F6_STRUCTURAL)

    return RiskFactorBreakdown(
        factor="special_structural_exposure",
        score=score,
        maximum_score=MAX_F6_STRUCTURAL,
        observed_value={"out_degree": out_degree, "path": file_path},
        status="evaluated",
        reason="; ".join(reasons) if reasons else "No special structural exposure factors observed.",
        evidence=[],
    )


def calculate_risk_score(
    finding: dict[str, Any],
    graph_is_available: bool = True,
    entry_points: list[dict[str, Any]] | None = None,
) -> tuple[float | None, str, list[RiskFactorBreakdown]]:
    """Calculate the deterministic review-risk score and factor breakdown for a finding.

    Args:
        finding: Enriched finding dictionary.
        graph_is_available: Whether dependency graph is available.
        entry_points: Optional list of repository entry point evidence.

    Returns:
        tuple (score, risk_level, factor_breakdown)
    """
    mapping_status = finding.get("mapping_status", MAPPING_STATUS_UNMAPPED)

    # If unmapped or graph unavailable, risk cannot be meaningfully assessed
    if not graph_is_available or mapping_status in (
        MAPPING_STATUS_UNMAPPED,
        MAPPING_STATUS_INVALID_PATH,
        MAPPING_STATUS_MISSING_FILE_PATH,
    ):
        f1 = score_dependency_exposure(finding, graph_is_available=graph_is_available)
        f2 = score_cycle_exposure(finding, graph_is_available=graph_is_available)
        f3 = score_entry_point_exposure(finding, entry_points=entry_points)
        f4 = score_test_impact_evidence(finding)
        f5 = score_finding_evidence(finding)
        f6 = score_structural_exposure(finding)
        return None, RISK_LEVEL_UNKNOWN, [f1, f2, f3, f4, f5, f6]

    # Evaluate factors
    f1 = score_dependency_exposure(finding, graph_is_available=True)
    f2 = score_cycle_exposure(finding, graph_is_available=True)
    f3 = score_entry_point_exposure(finding, entry_points=entry_points)
    f4 = score_test_impact_evidence(finding)
    f5 = score_finding_evidence(finding)
    f6 = score_structural_exposure(finding)

    factors = [f1, f2, f3, f4, f5, f6]
    raw_score = sum(f.score for f in factors)
    clamped_score = round(min(100.0, max(0.0, raw_score)), 1)
    risk_level = classify_risk(clamped_score, is_valid_assessment=True)

    return clamped_score, risk_level, factors

