from fastapi import APIRouter

from app.api.analyses import explain_finding

router = APIRouter(tags=["ai"])

# Route is exposed through /api/analyses/{analysis_id}/explain per shared API contract
__all__ = ["explain_finding", "router"]
