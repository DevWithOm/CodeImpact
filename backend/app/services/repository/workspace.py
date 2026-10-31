"""Workspace management for repository retrieval and static analysis isolation.

Handles temporary directory creation, isolation by analysis_id, and safe cleanup.
"""

import logging
import os
from pathlib import Path
import shutil
import tempfile
import uuid


logger = logging.getLogger(__name__)


def generate_analysis_id() -> str:
    """Generates a stable, unique analysis ID."""
    return f"an_{uuid.uuid4().hex[:12]}"


def create_workspace(analysis_id: str | None = None) -> tuple[str, str]:
    """Creates an isolated workspace directory for analysis.

    Args:
        analysis_id: Optional ID; if not provided, a new one is generated.

    Returns:
        tuple of (analysis_id, workspace_path)
    """
    aid = analysis_id or generate_analysis_id()
    # Use standard system temp base with a codeimpact prefix
    base_temp = Path(tempfile.gettempdir()) / "codeimpact" / "workspaces"
    base_temp.mkdir(parents=True, exist_ok=True)

    workspace_dir = base_temp / aid
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create standard report directory within workspace
    reports_dir = workspace_dir / ".codeimpact" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    return aid, str(workspace_dir.resolve())


def cleanup_workspace(workspace_path: str) -> bool:
    """Safely removes an analysis workspace.

    Args:
        workspace_path: Path to the workspace directory to remove.

    Returns:
        True if cleanup succeeded or directory did not exist, False on failure.
    """
    if not workspace_path or not os.path.exists(workspace_path):
        return True

    # Safety check: make sure we're not deleting system root or critical paths
    resolved = Path(workspace_path).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()

    try:
        # Verify workspace is inside temp directory
        resolved.relative_to(temp_root)
    except ValueError:
        logger.error("Refusing to delete path outside temp directory: %s", workspace_path)
        return False

    def on_rmtree_error(func, path, exc_info):
        # On Windows, git files might be read-only; clear readonly flag and retry
        try:
            os.chmod(path, 0o777)
            func(path)
        except Exception as exc:
            logger.warning("Failed to force-delete %s: %s", path, exc)

    try:
        shutil.rmtree(resolved, onerror=on_rmtree_error)
        return not os.path.exists(resolved)
    except Exception as exc:
        logger.error("Error cleaning up workspace %s: %s", workspace_path, exc)
        return False
