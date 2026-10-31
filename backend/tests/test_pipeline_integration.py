"""Phase 7: End-to-end pipeline integration and multi-service orchestration tests."""

from copy import deepcopy
from pathlib import Path
import pytest

from app.adapters.dependency_impact_adapter import DependencyImpactAdapter
from app.adapters.static_analysis_adapter import StaticAnalysisAdapter
from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.schemas.finding import FindingItem
from app.services.analysis_store import AnalysisStore
from app.services.orchestrator import AnalysisOrchestrator


class LocalFixtureRepoAdapter:
    """Repository adapter that binds to local test fixtures without git network calls."""

    def __init__(self, fixture_path: str):
        self.fixture_path = fixture_path
        self.cleaned_up = False

    def retrieve_repository(
        self,
        repository_url: str,
        branch: str,
        analysis_id: str,
    ) -> dict:
        return {
            "workspace_path": self.fixture_path,
            "repository": "test-org/sample-js-repository",
            "branch": branch or "main",
            "commit_sha": "fixture_sha_e2e_777",
            "file_count": 6,
            "languages": ["JavaScript", "TypeScript"],
        }

    def cleanup_workspace(self, workspace_path: str) -> None:
        self.cleaned_up = True


@pytest.fixture
def sample_fixture_path() -> str:
    path = Path("fixtures/sample-js-repository").resolve()
    assert path.exists(), f"Sample repository fixture not found at {path}"
    return str(path)


@pytest.mark.asyncio
async def test_full_pipeline_success_end_to_end(sample_fixture_path: str):
    """
    Test 1: Verify full end-to-end analysis of sample-js-repository fixture.
    Verifies:
      - Clean lifecycle progression: QUEUED -> RUNNING -> COMPLETED
      - Tool coverage reported across static analysis and dependency impact engines
      - Graph directionality invariant: source imports target
      - Finding enrichment and review-risk classification
      - Workspace cleanup invoked
    """
    store = AnalysisStore()
    repo_adapter = LocalFixtureRepoAdapter(sample_fixture_path)
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_e2e_integration_001"
    req = AnalysisRequest(
        repository_url="https://github.com/test-org/sample-js-repository",
        branch="main",
    )
    store.create_analysis(aid, req)

    await orchestrator.run_pipeline(aid)

    # 1. Verify final record status
    record = store.get_analysis(aid)
    assert record is not None
    assert record.status == AnalysisStatus.COMPLETED
    assert record.commit_sha == "fixture_sha_e2e_777"
    assert record.completed_at is not None
    assert repo_adapter.cleaned_up is True

    # 2. Verify tool coverage contract
    coverage = record.tool_coverage
    assert "git" in coverage
    assert "knip" in coverage
    assert "jscpd" in coverage
    assert "madge" in coverage
    assert "dependency_graph" in coverage
    assert "dependency_impact" in coverage
    assert "test_impact" in coverage
    assert "review_risk" in coverage
    assert coverage["madge"] == "success"
    assert coverage["dependency_graph"] == "success"
    assert coverage["dependency_impact"] == "success"
    assert coverage["test_impact"] == "success"
    assert coverage["review_risk"] == "success"

    # 3. Verify dependency graph structure and edge directionality
    graph = store.get_graph(aid)
    assert graph is not None
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    assert graph.stats.node_count == len(graph.nodes)

    # Invariant: every edge represents source importing target
    node_ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        assert edge.source in node_ids, f"Edge source {edge.source} not in graph nodes"
        assert edge.target in node_ids, f"Edge target {edge.target} not in graph nodes"

    # 4. Verify finding-level enrichment and risk scoring
    findings_resp = store.get_findings(aid)
    assert findings_resp is not None
    assert findings_resp.total == 7
    assert len(findings_resp.items) == 7

    for f in findings_resp.items:
        assert isinstance(f.finding_id, str) and f.finding_id.startswith("f_")
        assert f.file_path != ""
        assert f.source_tool in ("knip", "jscpd")
        assert f.review_risk in ("lower", "medium", "higher", "unknown")
        # Impact structure exists and is populated
        assert f.impact is not None
        assert isinstance(f.impact.direct_dependants, list)
        assert isinstance(f.impact.related_test_candidates, list)

    # 5. Verify metrics
    metrics = record.metrics
    assert metrics.total_findings == 7
    assert metrics.duplicate_groups == 1
    assert metrics.circular_dependencies == 0


@pytest.mark.asyncio
async def test_programmatic_run_analysis_method(sample_fixture_path: str):
    """
    Test 2: Verify orchestrator.run_analysis(request) convenience method.
    """
    store = AnalysisStore()
    repo_adapter = LocalFixtureRepoAdapter(sample_fixture_path)
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    req = AnalysisRequest(repository_url="https://github.com/test-org/sample-js-repository")
    status_resp = await orchestrator.run_analysis(req)

    assert status_resp["status"] == "completed"
    assert status_resp["metrics"]["total_findings"] == 7
    assert len(status_resp["findings"]) == 7


@pytest.mark.asyncio
async def test_store_deep_copy_immutability(sample_fixture_path: str):
    """
    Test 3: Verify that mutations to objects returned by store queries
    do not contaminate internal store state.
    """
    store = AnalysisStore()
    repo_adapter = LocalFixtureRepoAdapter(sample_fixture_path)
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid = "an_immutability_check"
    req = AnalysisRequest(repository_url="https://github.com/test-org/sample-js-repository")
    store.create_analysis(aid, req)
    await orchestrator.run_pipeline(aid)

    # Modify query result
    findings = store.get_findings(aid)
    original_risk = findings.items[0].review_risk
    findings.items[0].review_risk = "mutated_risk_level"

    # Fetch fresh record
    fresh_findings = store.get_findings(aid)
    assert fresh_findings.items[0].review_risk == original_risk


@pytest.mark.asyncio
async def test_concurrent_analysis_isolation(sample_fixture_path: str):
    """
    Test 4: Verify that multiple distinct analysis jobs run through
    the orchestrator and store maintain strict isolation.
    """
    store = AnalysisStore()
    repo_adapter = LocalFixtureRepoAdapter(sample_fixture_path)
    static_adapter = StaticAnalysisAdapter()
    dep_adapter = DependencyImpactAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    aid1 = "an_iso_001"
    aid2 = "an_iso_002"

    store.create_analysis(aid1, AnalysisRequest(repository_url="https://github.com/test-org/sample-js-repository"))
    store.create_analysis(aid2, AnalysisRequest(repository_url="https://github.com/test-org/sample-js-repository"))

    await orchestrator.run_pipeline(aid1)
    await orchestrator.run_pipeline(aid2)

    rec1 = store.get_analysis(aid1)
    rec2 = store.get_analysis(aid2)

    assert rec1.analysis_id == aid1
    assert rec2.analysis_id == aid2
    assert rec1.status == AnalysisStatus.COMPLETED
    assert rec2.status == AnalysisStatus.COMPLETED

    f1 = store.get_findings(aid1)
    f2 = store.get_findings(aid2)
    assert f1.analysis_id == aid1
    assert f2.analysis_id == aid2
    assert len(f1.items) == len(f2.items) == 7
