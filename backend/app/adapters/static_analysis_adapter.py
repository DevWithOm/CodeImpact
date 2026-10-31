import logging
from typing import Any

from app.adapters.base import StaticAnalysisAdapterProtocol
from app.adapters.repository_adapter import IntegrationPendingError

logger = logging.getLogger(__name__)


class StaticAnalysisAdapter(StaticAnalysisAdapterProtocol):
    """Adapter for Person 2 (OM_2) static code analysis tools (Knip, jscpd)."""

    def analyze_repository(
        self,
        workspace_path: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Calls Person 2's analyze_repository if available.
        Otherwise raises IntegrationPendingError.
        """
        try:
            from app.services.static_analysis import analyzer  # type: ignore

            if hasattr(analyzer, "analyze_repository") and callable(analyzer.analyze_repository):
                return analyzer.analyze_repository(workspace_path, analysis_id)
        except (ImportError, AttributeError) as exc:
            logger.info("Person 2 static analysis module not available yet: %s", exc)

        raise IntegrationPendingError(
            f"Static code analysis module (Person 2 - OM_2) is pending implementation for analysis {analysis_id}."
        )
