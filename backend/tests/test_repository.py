"""Tests for repository validation, workspace management, and retrieval logic."""

import os
from pathlib import Path
import pytest

from backend.app.services.repository.github_service import (
    RepositoryRetrievalError,
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
        "http://github.com/owner/repo",  # Non-HTTPS
        "git@github.com:owner/repo.git",  # SSH
        "https://gitlab.com/owner/repo",  # Non-GitHub
        "https://github.com/owner",  # Missing repo
        "https://github.com/owner/repo/subpath",  # Subpath
        "https://github.com/../repo",  # Path traversal
    ]
    for url in invalid_cases:
        with pytest.raises(RepositoryRetrievalError):
            validate_github_url(url)


def test_workspace_lifecycle():
    aid = generate_analysis_id()
    assert aid.startswith("an_")

    aid, ws_path = create_workspace(aid)
    assert os.path.exists(ws_path)
    assert os.path.isdir(ws_path)
    assert os.path.exists(os.path.join(ws_path, ".codeimpact", "reports"))

    # Cleanup
    cleaned = cleanup_workspace(ws_path)
    assert cleaned is True
    assert not os.path.exists(ws_path)


def test_path_traversal_protection(tmp_path):
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    child_file = base_dir / "safe.ts"
    child_file.write_text("console.log('safe');")

    outside_file = tmp_path / "outside.ts"
    outside_file.write_text("console.log('outside');")

    assert is_safe_path(str(base_dir), str(child_file)) is True
    assert is_safe_path(str(base_dir), str(outside_file)) is False
    assert is_safe_path(str(base_dir), str(base_dir / ".." / "outside.ts")) is False


def test_scan_repository_files(tmp_path):
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"name": "test"}')

    src = repo / "src"
    src.mkdir()
    (src / "index.ts").write_text("export const a = 1;")
    (src / "utils.js").write_text("module.exports = {};")

    # Ignored directory
    nm = repo / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "bad.js").write_text("ignore me")

    res = scan_repository_files(str(repo))
    assert res["has_package_json"] is True
    assert res["eligible_file_count"] == 2
    assert "TypeScript" in res["languages"]
    assert "JavaScript" in res["languages"]
    assert "src/index.ts" in res["files"]
    assert "src/utils.js" in res["files"]
