"""GitHub repository retrieval service.

Handles public GitHub HTTPS URL validation, shallow cloning, branch resolution,
commit SHA extraction, size/timeout restrictions, file filtering, and workspace management.
"""

import logging
import os
from pathlib import Path
import re

from backend.app.services.repository.workspace import create_workspace
from backend.app.utils.file_utils import get_directory_size_mb, is_safe_path, scan_repository_files
from backend.app.utils.subprocess_runner import run_command


logger = logging.getLogger(__name__)

# Strict regex for public GitHub HTTPS URLs only
GITHUB_HTTPS_REGEX = re.compile(
    r"^https://github\.com/(?P<owner>[a-zA-Z0-9_.-]+)/(?P<repo>[a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
)

# Restrictions
MAX_REPO_SIZE_MB = 200.0
MAX_FILE_COUNT = 10000
CLONE_TIMEOUT_SECONDS = 180


class RepositoryRetrievalError(Exception):
    """Raised when repository retrieval fails validation, security checks, or execution."""
    pass


def validate_github_url(url: str) -> tuple[str, str, str]:
    """Validates public GitHub HTTPS URL.

    Returns:
        tuple of (normalized_url, owner, repo_name)

    Raises:
        RepositoryRetrievalError if URL format is invalid, uses an unsupported host, or is insecure.
    """
    if not url or not isinstance(url, str):
        raise RepositoryRetrievalError("Repository URL must be a non-empty string.")

    cleaned_url = url.strip()

    # Reject non-GitHub hosts explicitly with clear messages
    if "gitlab.com" in cleaned_url or "bitbucket.org" in cleaned_url or "sourceforge.net" in cleaned_url:
        raise RepositoryRetrievalError(
            f"Unsupported host in URL '{cleaned_url}'. Only public GitHub repositories are supported."
        )

    match = GITHUB_HTTPS_REGEX.match(cleaned_url)
    if not match:
        raise RepositoryRetrievalError(
            f"Invalid GitHub URL: '{cleaned_url}'. Only public HTTPS GitHub URLs are supported "
            "(e.g., https://github.com/owner/repo)."
        )

    owner = match.group("owner")
    repo = match.group("repo")

    # Defense against path traversal or malicious symbols in names
    if ".." in owner or ".." in repo:
        raise RepositoryRetrievalError("Invalid repository URL: path traversal detected.")

    normalized_url = f"https://github.com/{owner}/{repo}.git"
    return normalized_url, owner, repo


def validate_branch_name(branch: str | None) -> str | None:
    """Validates git branch name to prevent flag injection or shell tampering."""
    if not branch or not branch.strip():
        return None

    clean_branch = branch.strip()
    # Reject flag injection, command chaining characters, or whitespace
    if clean_branch.startswith("-") or ";" in clean_branch or " " in clean_branch or "&" in clean_branch or "|" in clean_branch:
        raise RepositoryRetrievalError(f"Invalid branch name: '{clean_branch}'.")

    return clean_branch


def retrieve_repository(
    repository_url: str,
    branch: str | None = None,
    analysis_id: str | None = None,
) -> dict:
    """Retrieves a public GitHub repository into an isolated temporary workspace.

    Args:
        repository_url: Public HTTPS GitHub URL.
        branch: Optional branch name to checkout. If None, default branch is cloned.
        analysis_id: Optional unique analysis identifier.

    Returns:
        Dict conforming to the Phase 1 retrieval contract:
        {
            "workspace_path": "/tmp/codeimpact/an_001",
            "repository": "owner/repository",
            "branch": "main",
            "commit_sha": "abc123",
            "file_count": 120,
            "total_file_count": 150,
            "languages": ["JavaScript", "TypeScript"],
            "status": "retrieved",
            "warnings": []
        }

    Raises:
        RepositoryRetrievalError on validation, security violations, or git clone failures.
    """
    warnings: list[str] = []

    # 1. URL Validation
    normalized_url, owner, repo_name = validate_github_url(repository_url)
    full_repo_id = f"{owner}/{repo_name}"

    # 2. Branch Validation
    valid_branch = validate_branch_name(branch)

    # 3. Workspace Creation
    aid, workspace_path = create_workspace(analysis_id)

    # 4. Clone execution using shallow clone (--depth 1)
    clone_cmd = ["git", "clone", "--depth", "1"]
    if valid_branch:
        clone_cmd.extend(["--branch", valid_branch])

    clone_cmd.extend([normalized_url, workspace_path])

    clone_result = run_command(
        clone_cmd,
        timeout=CLONE_TIMEOUT_SECONDS,
        env={"GIT_TERMINAL_PROMPT": "0"},  # Never prompt for passwords
    )

    if not clone_result.succeeded:
        error_msg = clone_result.stderr.strip() or clone_result.stdout.strip()
        raise RepositoryRetrievalError(
            f"Failed to retrieve repository '{full_repo_id}'"
            + (f" on branch '{branch}'" if branch else "")
            + f": {error_msg}"
        )

    # 5. Extract Commit SHA
    sha_result = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace_path,
        timeout=10,
    )
    commit_sha = sha_result.stdout.strip() if sha_result.succeeded else "unknown"

    # 6. Extract actual resolved branch name
    branch_result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=workspace_path,
        timeout=10,
    )
    resolved_branch = branch_result.stdout.strip() if branch_result.succeeded else (valid_branch or "HEAD")

    # 7. Verify repository size restriction
    size_mb = get_directory_size_mb(workspace_path)
    if size_mb > MAX_REPO_SIZE_MB:
        raise RepositoryRetrievalError(
            f"Repository exceeds maximum allowed size ({size_mb} MB > {MAX_REPO_SIZE_MB} MB limit)."
        )

    # 8. Scan repository files and detect languages
    file_scan = scan_repository_files(workspace_path, max_files=MAX_FILE_COUNT)
    if file_scan["total_file_count"] > MAX_FILE_COUNT:
        raise RepositoryRetrievalError(
            f"Repository exceeds maximum allowed file count ({file_scan['total_file_count']} > {MAX_FILE_COUNT} files limit)."
        )

    if not file_scan["has_package_json"]:
        warnings.append("No root package.json found. Analysis may be limited or skipped.")

    if file_scan["eligible_file_count"] == 0:
        warnings.append("No JavaScript or TypeScript files detected in repository.")

    return {
        "workspace_path": workspace_path,
        "repository": full_repo_id,
        "branch": resolved_branch,
        "commit_sha": commit_sha,
        "file_count": file_scan["eligible_file_count"],
        "total_file_count": file_scan["total_file_count"],
        "languages": file_scan["languages"],
        "status": "retrieved",
        "warnings": warnings,
        "analysis_id": aid,
    }
