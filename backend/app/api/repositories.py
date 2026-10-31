import uuid
from fastapi import APIRouter, BackgroundTasks, status

from app.schemas.analysis import AnalysisCreatedResponse, AnalysisRequest
from app.services.analysis_store import analysis_store
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post(
    "/analyse",
    response_model=AnalysisCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start repository analysis",
    description="Validates repository URL, creates an in-memory analysis record, starts background analysis, and returns 202 Accepted.",
)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisCreatedResponse:
    analysis_id = f"an_{uuid.uuid4().hex[:8]}"
    repo_identifier = request.get_repository_identifier()

    # Create initial record in analysis store
    analysis_store.create_analysis(analysis_id=analysis_id, request=request)

    # Schedule background analysis pipeline
    background_tasks.add_task(orchestrator.run_pipeline, analysis_id)

    return AnalysisCreatedResponse(
        analysis_id=analysis_id,
        status="queued",
        repository=repo_identifier,
        branch=request.branch,
    )
