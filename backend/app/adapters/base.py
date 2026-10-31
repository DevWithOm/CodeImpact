from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RepositoryAdapterProtocol(Protocol):
    """Protocol for repository retrieval and workspace lifecycle."""

    def retrieve_repository(
        self,
        repository_url: str,
        branch: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Retrieves a public GitHub repository branch into a temporary directory.
        Returns metadata:
            {
                "workspace_path": str,
                "repository": str,
                "branch": str,
                "commit_sha": str | None,
                "file_count": int,
                "languages": list[str]
            }
        """
        ...

    def cleanup_workspace(self, workspace_path: str) -> None:
        """Safely cleans up the temporary workspace directory."""
        ...


@runtime_checkable
class StaticAnalysisAdapterProtocol(Protocol):
    """Protocol for Person 2's static code analysis module."""

    def analyze_repository(
        self,
        workspace_path: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Runs Knip and jscpd on workspace_path.
        Returns:
            {
                "findings": list[dict],
                "tool_coverage": dict[str, str], # e.g. {"knip": "success", "jscpd": "success"}
                "duplicate_groups": int
            }
        """
        ...


@runtime_checkable
class DependencyImpactAdapterProtocol(Protocol):
    """Protocol for Person 3's dependency graph and impact module."""

    def analyze_impact(
        self,
        workspace_path: str,
        findings: list[dict[str, Any]],
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Runs Madge and builds directed dependency graph, cycles, and enriched findings.
        Returns:
            {
                "graph": dict,              # {"nodes": [...], "edges": [...], "cycles": [...], "stats": {...}, "truncated": bool}
                "enriched_findings": list[dict],
                "tool_coverage": dict[str, str] # e.g. {"madge": "success"}
            }
        """
        ...
