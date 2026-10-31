from fastapi import APIRouter

from app.api.analyses import download_analysis_report

router = APIRouter(tags=["reports"])

# Route is exposed through /api/analyses/{analysis_id}/report per shared API contract
__all__ = ["download_analysis_report", "router"]
