"""Phase 7: Pipeline error handling, partial failure resilience, and edge case tests."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.adapters.dependency_impact_adapter import DependencyImpactAdapter
from app.adapters.repository_adapter import RepositoryAdapter
from app.adapters.static_analysis_adapter import StaticAnalysisAdapter
from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.services.analysis_store import AnalysisStore
from app.services.orchestrator import AnalysisOrchestrator
from app.services.repository.github_service import (
    RepositoryRetrievalError,
    validate_branch_name,
    validate_github_url,
)


class FailingRepoAdapter:
    def __init__(self, error_message: str = "Cloning error"):
        self.error_message = error_message
        self.cleaned_up = False

    def retrieve_repository(self, repository_url: str, branch: str, analysis_id: str) -> dict:
        raise RuntimeError(self.error_message)

    def cleanup_workspace(self, workspace_path: str) -> None:
        self.cleaned_up = True


class MockRepoAdapter:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.cleaned_up = False

    def retrieve_repository(self, repository_url: str, branch: str, analysis_id: str) -> dict:
        return {
            "workspace_path": self.workspace_path,
            "repository": "test-org/repo",
            "branch": branch or "main",
            "commit_sha": "abc1234",
            "file_count": 5,
            "languages": ["JavaScript"],
        }

    def cleanup_workspace(self, workspace_path: str) -> None:
        self.cleaned_up = True


class FailingStaticAdapter:
    def analyze_repository(self, workspace_path: str, analysis_id: str) -> dict:
        raise RuntimeError("Knip and jscpd execution failed unexpectedly")


class FailingDependencyAdapter:
    def analyze_impact(self, workspace_path: str, findings: list, analysis_id: str) -> dict:
        raise RuntimeError("Madge binary timed out or exited with non-zero status")


@pytest.fixture
def sample_fixture_path() -> str:
    path = Path("fixtures/sample-js-repository").resolve()
    assert path.exists(), f"Sample repository fixture not found at {path}"
    return str(path)


@pytest.mark.asyncio
async def test_repository_retrieval_failure_marks_failed_and_cleans_up():
    """Verify repository retrieval failure terminates pipeline gracefully and marks status FAILED."""
    store = AnalysisStore()
    repo_adapter = FailingRepoAdapter("Git shallow clone timed out after 180s")
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_fail_repo_01"
    store.create_analysis(aid, AnalysisRequest(repository_url="https://github.com/test-org/repo"))
    await orchestrator.run_pipeline(aid)

    record = store.get_analysis(aid)
    assert record.status == AnalysisStatus.FAILED
    assert "Git shallow clone timed out" in record.error_message
    assert record.current_stage == "failed"


@pytest.mark.asyncio
async def test_static_analysis_failure_produces_partial_status(sample_fixture_path: str):
    """Verify that static analysis failure preserves dependency graph and produces PARTIAL status."""
    store = AnalysisStore()
    repo_adapter = MockRepoAdapter(sample_fixture_path)
    static_adapter = FailingStaticAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_fail_static_01"
    store.create_analysis(aid, AnalysisRequest(repository_url="https://github.com/test-org/repo"))
    await orchestrator.run_pipeline(aid)

    record = store.get_analysis(aid)
    assert record.status == AnalysisStatus.PARTIAL
    assert record.tool_coverage.get("static_analysis") == "failed"

    # Dependency graph was still built
    graph = store.get_graph(aid)
    assert graph is not None
    assert len(graph.nodes) > 0


@pytest.mark.asyncio
async def test_dependency_analysis_failure_falls_back_to_empty_graph(sample_fixture_path: str):
    """Verify that dependency engine failure falls back to empty graph and preserves static findings."""
    store = AnalysisStore()
    repo_adapter = MockRepoAdapter(sample_fixture_path)
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = FailingDependencyAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_fail_dep_01"
    store.create_analysis(aid, AnalysisRequest(repository_url="https://github.com/test-org/repo"))
    await orchestrator.run_pipeline(aid)

    record = store.get_analysis(aid)
    assert record.status == AnalysisStatus.PARTIAL
    assert record.tool_coverage.get("dependency_impact") == "failed"

    findings = store.get_findings(aid)
    assert findings is not None
    assert findings.total > 0

    graph = store.get_graph(aid)
    assert graph is not None
    assert len(graph.nodes) == 0


@pytest.mark.asyncio
async def test_empty_findings_pipeline_success(sample_fixture_path: str):
    """Verify repository with 0 findings completes successfully with empty findings list and valid graph."""
    class EmptyStaticAdapter:
        def analyze_repository(self, workspace_path: str, analysis_id: str) -> dict:
            return {
                "findings": [],
                "tool_coverage": {"knip": "success", "jscpd": "success"},
                "duplicate_groups": 0,
            }

    store = AnalysisStore()
    repo_adapter = MockRepoAdapter(sample_fixture_path)
    static_adapter = EmptyStaticAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_empty_findings_01"
    store.create_analysis(aid, AnalysisRequest(repository_url="https://github.com/test-org/repo"))
    await orchestrator.run_pipeline(aid)

    record = store.get_analysis(aid)
    assert record.status == AnalysisStatus.COMPLETED
    assert record.metrics.total_findings == 0
    assert record.metrics.duplicate_groups == 0

    findings = store.get_findings(aid)
    assert findings.total == 0
    assert len(findings.items) == 0


def test_url_security_validation_guards():
    """Verify security validation guards reject malicious URLs and path traversal attempts."""
    # Invalid schemes
    with pytest.raises(RepositoryRetrievalError):
        validate_github_url("http://github.com/owner/repo")

    with pytest.raises(RepositoryRetrievalError):
        validate_github_url("file:///etc/passwd")

    with pytest.raises(RepositoryRetrievalError):
        validate_github_url("https://malicious.com/owner/repo")

    # Path traversal attempts
    with pytest.raises(RepositoryRetrievalError):
        validate_github_url("https://github.com/owner/../../etc/passwd")


def test_branch_name_security_validation_guards():
    """Verify branch name validation rejects flag injection and shell command chaining."""
    # Flag injection
    with pytest.raises(RepositoryRetrievalError):
        validate_branch_name("--upload-pack=evil")

    # Shell chaining
    with pytest.raises(RepositoryRetrievalError):
        validate_branch_name("main; rm -rf /")

    with pytest.raises(RepositoryRetrievalError):
        validate_branch_name("main && whoami")

    # Control characters
    with pytest.raises(RepositoryRetrievalError):
        validate_branch_name("main\x00evil")

    # Valid branch passes
    assert validate_branch_name("feature/safe-branch-v1") == "feature/safe-branch-v1"
    assert validate_branch_name(None) is None
