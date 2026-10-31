from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

try:
    from backend.app.schemas.analysis import (
        AnalysisMetrics,
        AnalysisRequest,
        AnalysisStatus,
        AnalysisStatusResponse,
    )
    from backend.app.schemas.finding import FindingDetail, FindingItem, FindingsListResponse
    from backend.app.schemas.graph import GraphResponse, GraphStats
except ImportError:
    from app.schemas.analysis import (
        AnalysisMetrics,
        AnalysisRequest,
        AnalysisStatus,
        AnalysisStatusResponse,
    )
    from app.schemas.finding import FindingDetail, FindingItem, FindingsListResponse
    from app.schemas.graph import GraphResponse, GraphStats


def compute_metrics(findings: list[FindingItem], graph: GraphResponse | None = None) -> AnalysisMetrics:
    higher = sum(1 for f in findings if getattr(f, "review_risk", None) == "higher")
    medium = sum(1 for f in findings if getattr(f, "review_risk", None) == "medium")
    lower = sum(1 for f in findings if getattr(f, "review_risk", None) == "lower")
    unknown = sum(1 for f in findings if getattr(f, "review_risk", None) in ("unknown", None, ""))
    duplicates = sum(1 for f in findings if getattr(f, "category", None) in ("duplicate_block", "duplicate_code"))

    test_candidates = 0
    for f in findings:
        impact = getattr(f, "impact", None)
        if impact and getattr(impact, "related_test_candidates", None):
            test_candidates += len(impact.related_test_candidates)
        elif getattr(f, "test_impact", None):
            ti = getattr(f, "test_impact")
            candidates = getattr(ti, "related_test_candidates", None) or getattr(ti, "direct_test_files", None)
            if candidates:
                test_candidates += len(candidates)

    cycles = len(graph.cycles) if graph and hasattr(graph, "cycles") else 0

    return AnalysisMetrics(
        total_findings=len(findings),
        higher_risk=higher,
        medium_risk=medium,
        lower_risk=lower,
        unknown_risk=unknown,
        circular_dependencies=cycles,
        duplicate_groups=duplicates,
        test_candidates=test_candidates,
    )


@dataclass
class AnalysisRecord:
    analysis_id: str
    repository: str
    repository_url: str
    branch: str
    status: AnalysisStatus
    current_stage: str | None = None
    progress: int = 5
    message: str | None = "Request accepted and queued"
    commit_sha: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)
    tool_coverage: dict[str, str] = field(default_factory=dict)
    error_message: str | None = None
    findings: list[FindingItem] = field(default_factory=list)
    graph: GraphResponse | None = None

    def to_status_response(self) -> AnalysisStatusResponse:
        return AnalysisStatusResponse(
            analysis_id=self.analysis_id,
            repository=self.repository,
            repository_url=self.repository_url,
            branch=self.branch,
            commit_sha=self.commit_sha,
            status=self.status,
            current_stage=self.current_stage,
            progress=self.progress,
            stage_progress=self.progress,
            message=self.message,
            created_at=self.created_at,
            completed_at=self.completed_at,
            metrics=self.metrics,
            tool_coverage=self.tool_coverage,
            error_message=self.error_message,
        )


STAGE_PROGRESS_MAP: dict[str, tuple[int, str]] = {
    "queued": (5, "Request accepted and queued"),
    "cloning": (15, "Retrieving repository via shallow clone"),
    "static_analysis": (30, "Running Knip and jscpd static analysis"),
    "dependency_analysis": (55, "Analyzing dependencies, topology, and impact"),
    "risk_scoring": (85, "Calculating review risk and explanations"),
    "result_assembly": (95, "Assembling unified analysis results"),
    "completed": (100, "Analysis completed successfully"),
    "partial": (100, "Analysis completed with partial tool coverage"),
    "failed": (0, "Analysis pipeline failed"),
}


class AnalysisStore:
    """Thread-safe in-memory store for CodeImpact analysis jobs and findings."""

    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}
        self._lock = threading.RLock()

    def create_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisStatusResponse:
        with self._lock:
            repo_id = request.get_repository_identifier()
            record = AnalysisRecord(
                analysis_id=analysis_id,
                repository=repo_id,
                repository_url=request.repository_url,
                branch=request.branch,
                status=AnalysisStatus.QUEUED,
                current_stage="queued",
                created_at=datetime.now(timezone.utc),
                graph=GraphResponse(
                    analysis_id=analysis_id,
                    nodes=[],
                    edges=[],
                    cycles=[],
                    stats=GraphStats(node_count=0, edge_count=0, cycle_count=0),
                    truncated=False,
                ),
            )
            self._records[analysis_id] = record
            return record.to_status_response()

    def get_analysis(self, analysis_id: str) -> AnalysisStatusResponse | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None
            return record.to_status_response()

    def update_status(
        self,
        analysis_id: str,
        status: AnalysisStatus,
        stage: str | None = None,
        error_message: str | None = None,
        progress: int | None = None,
        message: str | None = None,
    ) -> AnalysisStatusResponse | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None

            record.status = status
            if stage is not None:
                record.current_stage = stage
                if stage in STAGE_PROGRESS_MAP:
                    default_prog, default_msg = STAGE_PROGRESS_MAP[stage]
                    record.progress = progress if progress is not None else default_prog
                    record.message = message or default_msg
            elif progress is not None:
                record.progress = progress
            if message is not None:
                record.message = message

            if status == AnalysisStatus.RUNNING and record.started_at is None:
                record.started_at = datetime.now(timezone.utc)

            if status in (AnalysisStatus.COMPLETED, AnalysisStatus.PARTIAL, AnalysisStatus.FAILED):
                record.completed_at = datetime.now(timezone.utc)
                if status in (AnalysisStatus.COMPLETED, AnalysisStatus.PARTIAL):
                    record.progress = 100
                    record.message = "Analysis completed successfully"

            if error_message is not None:
                record.error_message = error_message
                record.message = error_message

            return record.to_status_response()

    def update_results(
        self,
        analysis_id: str,
        findings: list[FindingItem],
        graph: GraphResponse,
        tool_coverage: dict[str, str],
        commit_sha: str | None = None,
        status: AnalysisStatus = AnalysisStatus.COMPLETED,
        error_message: str | None = None,
    ) -> AnalysisStatusResponse | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None

            record.findings = deepcopy(findings)
            record.graph = deepcopy(graph)
            record.tool_coverage = deepcopy(tool_coverage)
            if commit_sha:
                record.commit_sha = commit_sha

            record.metrics = compute_metrics(findings, graph)
            record.status = status
            record.current_stage = status.value
            record.progress = 100
            record.message = "Analysis completed successfully" if status == AnalysisStatus.COMPLETED else "Analysis completed with partial coverage"
            record.completed_at = datetime.now(timezone.utc)
            if error_message:
                record.error_message = error_message

            return record.to_status_response()

    def get_findings(
        self,
        analysis_id: str,
        category: str | None = None,
        review_risk: str | None = None,
        evidence_class: str | None = None,
        source_tool: str | None = None,
        path: str | None = None,
        search: str | None = None,
        sort: str | None = "risk_desc",
        page: int = 1,
        page_size: int = 50,
    ) -> FindingsListResponse | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None

            items = list(record.findings)

            # Filtering
            if category:
                items = [f for f in items if f.category == category]
            if review_risk:
                items = [f for f in items if f.review_risk == review_risk]
            if evidence_class:
                items = [f for f in items if f.evidence_class == evidence_class]
            if source_tool:
                items = [f for f in items if f.source_tool == source_tool]
            if path:
                items = [f for f in items if path.lower() in f.file_path.lower()]
            if search:
                term = search.lower()
                items = [
                    f
                    for f in items
                    if term in f.title.lower()
                    or term in f.file_path.lower()
                    or term in f.description.lower()
                    or (f.symbol and term in f.symbol.lower())
                ]

            # Sorting
            risk_weights = {"higher": 4, "medium": 3, "lower": 2, "unknown": 1}
            if sort == "risk_desc":
                items.sort(key=lambda x: risk_weights.get(x.review_risk, 0), reverse=True)
            elif sort == "risk_asc":
                items.sort(key=lambda x: risk_weights.get(x.review_risk, 0))
            elif sort == "path_asc":
                items.sort(key=lambda x: x.file_path.lower())

            # Pagination
            total = len(items)
            page = max(1, page)
            page_size = max(1, min(100, page_size))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_items = deepcopy(items[start_idx:end_idx])

            return FindingsListResponse(
                analysis_id=analysis_id,
                items=paginated_items,
                total=total,
                page=page,
                page_size=page_size,
                tool_coverage=deepcopy(record.tool_coverage),
            )

    def get_finding(self, analysis_id: str, finding_id: str) -> FindingDetail | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None

            for f in record.findings:
                if f.finding_id == finding_id:
                    detail_data = f.model_dump()
                    detail_data["limitations"] = [
                        "Static analysis reports absence of static references and cannot prove runtime reachability."
                    ]
                    return FindingDetail(**detail_data)

            return None

    def get_graph(self, analysis_id: str) -> GraphResponse | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None
            if record.graph is None:
                return GraphResponse(
                    analysis_id=analysis_id,
                    nodes=[],
                    edges=[],
                    cycles=[],
                    stats=GraphStats(node_count=0, edge_count=0, cycle_count=0),
                    truncated=False,
                )
            return deepcopy(record.graph)

    def get_record(self, analysis_id: str) -> AnalysisRecord | None:
        with self._lock:
            record = self._records.get(analysis_id)
            if record is None:
                return None
            return deepcopy(record)

    def clear(self) -> None:
        """Clear all records (intended for testing)."""
        with self._lock:
            self._records.clear()


# Global singleton store instance for the application process
analysis_store = AnalysisStore()
