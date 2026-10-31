import logging
from typing import Any

from app.adapters.base import DependencyImpactAdapterProtocol
from app.adapters.repository_adapter import IntegrationPendingError

logger = logging.getLogger(__name__)


class DependencyImpactAdapter(DependencyImpactAdapterProtocol):
    """Adapter for Person 3 (SAMAR_3) dependency graph and impact analysis (Madge)."""

    def analyze_impact(
        self,
        workspace_path: str,
        findings: list[dict[str, Any]],
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Calls Person 3's analyze_impact if available.
        Otherwise raises IntegrationPendingError.
        """
        try:
            from app.services.dependency_impact import impact_analyzer  # type: ignore

            if hasattr(impact_analyzer, "analyze_impact") and callable(impact_analyzer.analyze_impact):
                return impact_analyzer.analyze_impact(workspace_path, findings, analysis_id)
        except (ImportError, AttributeError) as exc:
            logger.info("Person 3 dependency impact module not available yet: %s", exc)

        raise IntegrationPendingError(
            f"Dependency and impact analysis module (Person 3 - SAMAR_3) is pending implementation for analysis {analysis_id}."
        )
