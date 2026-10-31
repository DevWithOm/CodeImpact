"""Comprehensive unit tests for repository retrieval, security checks, and workspace lifecycle."""

import os
from pathlib import Path
import pytest

from backend.app.services.repository.github_service import (
    RepositoryRetrievalError,
    validate_branch_name,
    validate_github_url,
)
from backend.app.services.repository.workspace import (
    cleanup_workspace,
    create_workspace,
    generate_analysis_id,
)
from backend.app.utils.file_utils import (
    get_directory_size_mb,
    is_safe_path,
    scan_repository_files,
)
from backend.app.utils.subprocess_runner import run_command


def test_validate_github_url_valid():
    valid_cases = [
        ("https://github.com/facebook/react", "facebook", "react"),
        ("https://github.com/facebook/react.git", "facebook", "react"),
        ("https://github.com/facebook/react/", "facebook", "react"),
        ("https://github.com/user-name/repo_123.test", "user-name", "repo_123.test"),
    ]
    for url, expected_owner, expected_repo in valid_cases:
        norm, owner, repo = validate_github_url(url)
        assert owner == expected_owner
        assert repo == expected_repo
        assert norm == f"https://github.com/{expected_owner}/{expected_repo}.git"


def test_validate_github_url_invalid():
    invalid_cases = [
        "",
        "http://github.com/owner/repo",  # Insecure HTTP
        "git@github.com:owner/repo.git",  # SSH
        "https://github.com/owner",  # Missing repo component
        "https://github.com/owner/repo/subpath",  # Subpath appended
        "https://github.com/../repo",  # Path traversal injection
        "https://github.com/owner/..",  # Traversal in repo
    ]
    for url in invalid_cases:
        with pytest.raises(RepositoryRetrievalError):
            validate_github_url(url)


def test_unsupported_hosts():
    unsupported_hosts = [
        "https://gitlab.com/gitlab-org/gitlab",
        "https://bitbucket.org/atlassian/repo",
        "https://sourceforge.net/p/project/code",
        "https://custom-git.internal.net/repo",
    ]
    for url in unsupported_hosts:
        with pytest.raises(RepositoryRetrievalError) as exc_info:
            validate_github_url(url)
        # Should explicitly reject non-GitHub hosts
        assert "Only public" in str(exc_info.value) or "Unsupported host" in str(exc_info.value) or "Invalid GitHub URL" in str(exc_info.value)


def test_branch_validation():
    # Valid branch names
    assert validate_branch_name("main") == "main"
    assert validate_branch_name("feat/user-auth") == "feat/user-auth"
    assert validate_branch_name("v1.0.0-beta.1") == "v1.0.0-beta.1"
    assert validate_branch_name(None) is None
    assert validate_branch_name("  ") is None

    # Malicious branch names (flag injection, command chaining)
    malicious_branches = [
        "--upload-pack=malicious",
        "-b; evil_cmd",
        "main && whoami",
        "feature branch with spaces",
        "test;rm -rf /",
    ]
    for branch in malicious_branches:
        with pytest.raises(RepositoryRetrievalError):
            validate_branch_name(branch)


def test_workspace_lifecycle():
    aid = generate_analysis_id()
    assert aid.startswith("an_")

    aid, ws_path = create_workspace(aid)
    assert os.path.exists(ws_path)
    assert os.path.isdir(ws_path)
    assert os.path.exists(os.path.join(ws_path, ".codeimpact", "reports"))

    # Cleanup safely
    cleaned = cleanup_workspace(ws_path)
    assert cleaned is True
    assert not os.path.exists(ws_path)


def test_path_traversal_and_symlink_protection(tmp_path):
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    child_file = base_dir / "safe.ts"
    child_file.write_text("console.log('safe');")

    outside_file = tmp_path / "outside.ts"
    outside_file.write_text("console.log('outside');")

    # Regular files
    assert is_safe_path(str(base_dir), str(child_file)) is True
    assert is_safe_path(str(base_dir), str(outside_file)) is False
    assert is_safe_path(str(base_dir), str(base_dir / ".." / "outside.ts")) is False

    # Symlink escape check
    try:
        symlink_file = base_dir / "symlink_escape.ts"
        symlink_file.symlink_to(outside_file)
        # is_safe_path resolves realpath and must detect escape
        assert is_safe_path(str(base_dir), str(symlink_file)) is False
    except (OSError, NotImplementedError):
        # On Windows without developer mode/privilege, symlinks might not be permitted
        pass


def test_scan_repository_files_and_filtering(tmp_path):
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "test"}')

    src = repo / "src"
    src.mkdir()
    (src / "index.ts").write_text("export const a = 1;")
    (src / "utils.js").write_text("module.exports = {};")
    (src / "component.tsx").write_text("export const C = () => null;")

    # Ignored directories
    for ignored in ("node_modules", ".git", "dist", "build", "coverage", ".codeimpact"):
        ign_dir = repo / ignored
        ign_dir.mkdir()
        (ign_dir / "ignored.js").write_text("// ignore me")

    res = scan_repository_files(str(repo))
    assert res["has_package_json"] is True
    assert res["eligible_file_count"] == 3
    assert "TypeScript" in res["languages"]
    assert "JavaScript" in res["languages"]
    assert "src/index.ts" in res["files"]
    assert "src/utils.js" in res["files"]
    assert "src/component.tsx" in res["files"]
    # Verify ignored files not listed
    assert not any("node_modules" in f for f in res["files"])
    assert not any(".git" in f for f in res["files"])


def test_subprocess_timeout_handling():
    # Executing a sleep command with a shorter timeout must return timed_out=True
    py_code = "import time; time.sleep(10)"
    res = run_command(["python", "-c", py_code], timeout=1)
    assert res.timed_out is True
    assert res.succeeded is False
    assert "timed out after 1 seconds" in res.stderr
