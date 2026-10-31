import logging
from typing import Any

from app.adapters.base import StaticAnalysisAdapterProtocol

logger = logging.getLogger(__name__)


class StaticAnalysisAdapter(StaticAnalysisAdapterProtocol):
    """Adapter for Person 2 (OM_2) static code analysis tools (Knip, jscpd)."""

    def analyze_repository(
        self,
        workspace_path: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """Calls Person 2 (OM_2) static code analysis service."""
        try:
            from backend.app.services.static_analysis.analyzer import analyze_repository
        except ImportError:
            from app.services.static_analysis.analyzer import analyze_repository

        return analyze_repository(workspace_path, analysis_id=analysis_id)
