import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from app.adapters.base import RepositoryAdapterProtocol

logger = logging.getLogger(__name__)


class IntegrationPendingError(RuntimeError):
    """Raised when an external teammate module is pending implementation."""
    pass


class RepositoryAdapter(RepositoryAdapterProtocol):
    """Adapter for repository retrieval and safe workspace management."""

    def retrieve_repository(
        self,
        repository_url: str,
        branch: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """Calls Person 2 (OM_2) repository retrieval service."""
        try:
            from backend.app.services.repository.github_service import retrieve_repository
        except ImportError:
            from app.services.repository.github_service import retrieve_repository

        return retrieve_repository(
            repository_url=repository_url,
            branch=branch,
            analysis_id=analysis_id,
        )

    def cleanup_workspace(self, workspace_path: str) -> None:
        """
        Safely deletes only the temporary analysis directory created for this run.
        Guards against accidental deletion of project workspace or root paths.
        """
        if not workspace_path or not isinstance(workspace_path, str):
            return

        target = Path(workspace_path).resolve()
        temp_dir = Path(tempfile.gettempdir()).resolve()
        cwd = Path.cwd().resolve()

        # Safety check: must reside inside system temp directory and must not be root or cwd
        is_safe_temp = target != temp_dir and (temp_dir in target.parents)
        is_not_cwd = target != cwd and target not in cwd.parents and cwd not in target.parents

        if is_safe_temp and is_not_cwd and target.exists() and target.is_dir():
            try:
                shutil.rmtree(target, ignore_errors=True)
                logger.info("Cleaned up workspace at %s", target)
            except Exception as exc:
                logger.warning("Failed to remove workspace %s: %s", target, exc)
        else:
            logger.warning("Workspace cleanup skipped for potentially unsafe path: %s", target)
