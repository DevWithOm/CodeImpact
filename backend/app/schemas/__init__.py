"""Backend schemas package."""

from backend.app.schemas.ai import ExplainRequest, ExplainResponse
from backend.app.schemas.analysis import (
    AnalysisCreatedResponse,
    AnalysisMetrics,
    AnalysisRequest,
    AnalysisResult,
    AnalysisStage,
    AnalysisStatus,
    AnalysisStatusResponse,
    ToolCoverage,
    ToolCoverageItem,
    ToolStatus,
)
from backend.app.schemas.common import ErrorDetail, ErrorResponse
from backend.app.schemas.evidence import (
    EvidenceItem,
    EvidenceStatus,
    FindingImpact,
    TestCandidate,
)
from backend.app.schemas.finding import (
    DirectDependant,
    EnrichedFinding,
    EvidenceClass,
    Finding,
    FindingCategory,
    FindingDetail,
    FindingEvidenceItem,
    FindingImpactSummary,
    FindingItem,
    FindingsListResponse,
    ImpactEvidence,
    ReviewRisk,
)
from backend.app.schemas.graph import (
    DependencyGraphResponse,
    GraphData,
    GraphEdge,
    GraphNode,
    GraphResponse,
    GraphStats,
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
    TestImpactAnalysisResult,
    TestImpactSummary,
)

__all__ = [
    # AI
    "ExplainRequest",
    "ExplainResponse",
    # Analysis
    "AnalysisRequest",
    "AnalysisCreatedResponse",
    "AnalysisStatusResponse",
    "AnalysisMetrics",
    "AnalysisStatus",
    "AnalysisStage",
    "AnalysisResult",
    "ToolCoverage",
    "ToolCoverageItem",
    "ToolStatus",
    # Common
    "ErrorDetail",
    "ErrorResponse",
    # Evidence
    "EvidenceItem",
    "EvidenceStatus",
    "FindingImpact",
    "TestCandidate",
    # Finding
    "Finding",
    "FindingItem",
    "FindingDetail",
    "FindingsListResponse",
    "FindingEvidenceItem",
    "EnrichedFinding",
    "ImpactEvidence",
    "DirectDependant",
    "FindingImpactSummary",
    "FindingCategory",
    "EvidenceClass",
    "ReviewRisk",
    # Graph
    "GraphNode",
    "GraphEdge",
    "GraphStats",
    "GraphData",
    "GraphResponse",
    "DependencyGraphResponse",
    # Test Impact
    "TestImpactSummary",
    "FindingTestImpact",
    "FrameworkEvidence",
    "EntryPointEvidence",
    "TestImpactAnalysisResult",
    # Risk
    "RiskFactorBreakdown",
    "RiskAssessment",
    "FindingRiskResult",
    "RiskSummary",
    "RiskAnalysisResult",
]
