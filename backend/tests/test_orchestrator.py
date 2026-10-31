import pytest

from app.schemas.analysis import AnalysisRequest, AnalysisStatus
from app.services.analysis_store import AnalysisStore
from app.services.orchestrator import AnalysisOrchestrator


class MockRepoAdapter:
    def __init__(self, should_fail: bool = False, workspace_path: str = "/tmp/mock_repo"):
        self.should_fail = should_fail
        self.workspace_path = workspace_path
        self.cleaned_up = False

    def retrieve_repository(self, repository_url: str, branch: str, analysis_id: str) -> dict:
        if self.should_fail:
            raise RuntimeError("Network timeout while cloning repository")
        return {
            "workspace_path": self.workspace_path,
            "repository": repository_url,
            "branch": branch,
            "commit_sha": "abc1234",
            "file_count": 10,
            "languages": ["TypeScript"],
        }

    def cleanup_workspace(self, workspace_path: str) -> None:
        self.cleaned_up = True


class MockStaticAdapter:
    def __init__(self, should_fail: bool = False, findings: list | None = None):
        self.should_fail = should_fail
        self.findings = findings if findings is not None else [
            {
                "finding_id": "f_1",
                "category": "unused_export",
                "title": "Unused func",
                "file_path": "src/utils.ts",
                "source_tool": "knip",
                "description": "Exported symbol not referenced",
                "review_risk": "medium",
            }
        ]

    def analyze_repository(self, workspace_path: str, analysis_id: str) -> dict:
        if self.should_fail:
            raise RuntimeError("Knip failed with exit code 1")
        return {
            "findings": self.findings,
            "tool_coverage": {"knip": "success", "jscpd": "success"},
            "duplicate_groups": 0,
        }


class MockDependencyAdapter:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def analyze_impact(self, workspace_path: str, findings: list, analysis_id: str) -> dict:
        if self.should_fail:
            raise RuntimeError("Madge failed to parse entry point")
        return {
            "graph": {
                "nodes": [{"id": "src/utils.ts", "label": "utils.ts", "file_path": "src/utils.ts"}],
                "edges": [],
                "cycles": [],
                "stats": {"node_count": 1, "edge_count": 0, "cycle_count": 0},
            },
            "enriched_findings": findings,
            "tool_coverage": {"madge": "success"},
        }


@pytest.mark.asyncio
async def test_orchestrator_success_pipeline():
    store = AnalysisStore()
    repo_adapter = MockRepoAdapter()
    static_adapter = MockStaticAdapter()
    dep_adapter = MockDependencyAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_orch_1", req)

    await orchestrator.run_pipeline("an_orch_1")

    record = store.get_analysis("an_orch_1")
    assert record.status == AnalysisStatus.COMPLETED
    assert record.commit_sha == "abc1234"
    assert record.metrics.total_findings == 1
    assert repo_adapter.cleaned_up is True

    findings = store.get_findings("an_orch_1")
    assert findings is not None
    assert len(findings.items) == 1

    graph = store.get_graph("an_orch_1")
    assert graph is not None
    assert len(graph.nodes) == 1


@pytest.mark.asyncio
async def test_orchestrator_retrieval_failure():
    store = AnalysisStore()
    repo_adapter = MockRepoAdapter(should_fail=True)
    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=MockStaticAdapter(),
        dependency_adapter=MockDependencyAdapter(),
    )

    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_orch_2", req)

    await orchestrator.run_pipeline("an_orch_2")

    record = store.get_analysis("an_orch_2")
    assert record.status == AnalysisStatus.FAILED
    assert "Network timeout" in record.error_message


@pytest.mark.asyncio
async def test_orchestrator_partial_failure_tool_error():
    store = AnalysisStore()
    repo_adapter = MockRepoAdapter()
    # static fails, but dep returns graph
    static_adapter = MockStaticAdapter(should_fail=True)
    dep_adapter = MockDependencyAdapter()

    orchestrator = AnalysisOrchestrator(
        store=store,
        repo_adapter=repo_adapter,
        static_adapter=static_adapter,
        dependency_adapter=dep_adapter,
    )

    req = AnalysisRequest(repository_url="https://github.com/owner/repo")
    store.create_analysis("an_orch_3", req)

    await orchestrator.run_pipeline("an_orch_3")

    record = store.get_analysis("an_orch_3")
    assert record.status == AnalysisStatus.PARTIAL
    assert record.tool_coverage["static_analysis"] == "failed"
    assert record.tool_coverage["madge"] == "success"
    assert repo_adapter.cleaned_up is True
