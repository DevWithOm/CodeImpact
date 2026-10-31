from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.ai import ExplainRequest, ExplainResponse
from app.schemas.analysis import AnalysisStatusResponse
from app.schemas.finding import FindingDetail, FindingsListResponse
from app.schemas.graph import GraphResponse
from app.services.ai import AIServiceUnavailableError, gemini_service
from app.services.analysis_store import analysis_store

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get(
    "/{analysis_id}",
    response_model=AnalysisStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analysis status and metrics",
    description="Returns current status, progress stage, tool coverage, and summary metrics for an analysis job.",
)
async def get_analysis_status(analysis_id: str) -> AnalysisStatusResponse:
    analysis = analysis_store.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )
    return analysis


@router.get(
    "/{analysis_id}/findings",
    response_model=FindingsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List analysis findings",
    description="Returns a filterable, paginated list of dead code and duplicate findings for an analysis job.",
)
async def get_analysis_findings(
    analysis_id: str,
    category: str | None = Query(default=None, description="Filter by category (unused_export, unused_file, etc.)"),
    review_risk: str | None = Query(default=None, description="Filter by review risk (higher, medium, lower, unknown)"),
    evidence_class: str | None = Query(default=None, description="Filter by evidence class (strong, inconclusive, contradictory)"),
    source_tool: str | None = Query(default=None, description="Filter by source tool (knip, jscpd)"),
    path: str | None = Query(default=None, description="Substring filter for file path"),
    search: str | None = Query(default=None, description="Free text search on title, symbol, or description"),
    sort: str | None = Query(default="risk_desc", description="Sort order: risk_desc, risk_asc, path_asc"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
) -> FindingsListResponse:
    if analysis_store.get_analysis(analysis_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )

    findings = analysis_store.get_findings(
        analysis_id=analysis_id,
        category=category,
        review_risk=review_risk,
        evidence_class=evidence_class,
        source_tool=source_tool,
        path=path,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    if findings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )
    return findings


@router.get(
    "/{analysis_id}/findings/{finding_id}",
    response_model=FindingDetail,
    status_code=status.HTTP_200_OK,
    summary="Get single finding detail",
    description="Returns full evidence, risk factors, impact analysis, and test candidates for a specific finding.",
)
async def get_finding_detail(analysis_id: str, finding_id: str) -> FindingDetail:
    if analysis_store.get_analysis(analysis_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )

    finding = analysis_store.get_finding(analysis_id, finding_id)
    if finding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found in analysis '{analysis_id}'.",
        )
    return finding


@router.get(
    "/{analysis_id}/graph",
    response_model=GraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dependency graph",
    description="Returns the directed dependency graph, circular dependency cycles, and graph statistics.",
)
async def get_analysis_graph(analysis_id: str) -> GraphResponse:
    if analysis_store.get_analysis(analysis_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )

    graph = analysis_store.get_graph(analysis_id)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph for analysis '{analysis_id}' was not found.",
        )
    return graph


@router.post(
    "/{analysis_id}/explain",
    response_model=ExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI explanation for finding",
    description="Generates an evidence-grounded AI explanation and cleanup recommendation for a specific finding using Gemini.",
)
async def explain_finding(analysis_id: str, request: ExplainRequest) -> ExplainResponse:
    analysis = analysis_store.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' was not found.",
        )

    finding = analysis_store.get_finding(analysis_id, request.finding_id)
    if finding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{request.finding_id}' not found in analysis '{analysis_id}'.",
        )

    try:
        return await gemini_service.explain_finding(
            finding=finding,
            repo_name=analysis.repository,
            fallback_on_error=False,
        )
    except AIServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
