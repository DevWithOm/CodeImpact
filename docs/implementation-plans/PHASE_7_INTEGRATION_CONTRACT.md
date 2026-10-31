# PHASE 7 INTEGRATION CONTRACT: SERVICE ORCHESTRATION

**Project:** CodeImpact — Evidence-Based Codebase Intelligence & Safe Refactoring  
**Version:** 1.0.0  
**Effective Date:** 2026-10-31  
**Scope:** Runtime protocols, service inputs/outputs, error states, and invariant contracts.

---

## 1. Overview & Service Architecture

The CodeImpact pipeline connects three primary subsystem boundaries:
1. **Repository Retrieval & Security Boundary (OM_2)**
2. **Static Code Analysis Engine (OM_2)**
3. **Dependency & Impact Engine (SAMAR_3)**
4. **FastAPI Service & Analysis Store (TANUJA_4)**

Communication occurs exclusively through strongly typed adapter protocols defined in `app/adapters/base.py`.

```
[Client / API Request]
         |
         v
[AnalysisOrchestrator]
         |
         +--> [RepositoryAdapter] ------------> Clones repository to isolated temp directory
         |
         +--> [StaticAnalysisAdapter] --------> Executes Knip + jscpd, emits raw findings
         |
         +--> [DependencyImpactAdapter] -----> Single-pass Madge, builds graph, enriches findings,
         |                                     maps test candidates, evaluates review risk
         v
[AnalysisStore] <---------------------------- Updates results, status, metrics, tool coverage
         |
         +--> [GeminiService (Optional)] -----> Grounded explanation generation on demand
         |
         +--> [ReportGenerator] --------------> Markdown / JSON audit reports
```

---

## 2. Service Protocol Contracts

### 2.1 RepositoryAdapterProtocol
```python
class RepositoryAdapterProtocol(Protocol):
    def retrieve_repository(
        self,
        repository_url: str,
        branch: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Returns:
            {
                "workspace_path": str,   # Path to cloned workspace
                "repository": str,       # Normalized 'owner/repo'
                "branch": str,           # Checked-out branch
                "commit_sha": str,       # Resolved Git commit SHA
                "file_count": int,       # Number of files discovered
                "languages": list[str],  # Discovered programming languages
            }
        Raises:
            RepositoryRetrievalError: If URL is invalid, branch name is unsafe, or clone fails.
        """
        ...

    def cleanup_workspace(self, workspace_path: str) -> None:
        """Deletes only temporary analysis workspaces; guards against workspace/system root deletion."""
        ...
```

### 2.2 StaticAnalysisAdapterProtocol
```python
class StaticAnalysisAdapterProtocol(Protocol):
    def analyze_repository(
        self,
        workspace_path: str,
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Returns:
            {
                "findings": list[dict],        # Normalized Knip and jscpd findings
                "tool_coverage": dict[str, Any], # e.g. {"knip": {"status": "completed", ...}}
                "duplicate_groups": int,       # Count of duplicate blocks
            }
        """
        ...
```

### 2.3 DependencyImpactAdapterProtocol
```python
class DependencyImpactAdapterProtocol(Protocol):
    def analyze_impact(
        self,
        workspace_path: str,
        findings: list[dict[str, Any]],
        analysis_id: str,
    ) -> dict[str, Any]:
        """
        Executes single-pass Madge -> Graph -> Direct Impact -> Test Impact -> Review Risk.
        Returns:
            {
                "graph": dict[str, Any],            # Nodes, edges, cycles, stats
                "enriched_findings": list[dict],    # Findings augmented with impact, tests, risk
                "risk_summary": dict[str, Any],     # Aggregate risk score distributions
                "detected_frameworks": list[str],   # Test frameworks (jest, mocha, etc.)
                "entry_points": list[str],          # Discovered application entry points
                "tool_coverage": dict[str, str],    # Status for madge, graph, impact, tests, risk
            }
        """
        ...
```

---

## 3. Invariants & Guarantees

1. **Non-Destructive Invariant:** Target repository code is NEVER executed, evaluated, built, compiled, or auto-deleted.
2. **Single-Pass Madge Invariant:** Madge AST extraction runs exactly once per analysis session. Downstream modules share the resulting dependency graph.
3. **Graph Direction Invariant:** An edge `(A -> B)` strictly signifies that file `A` imports or depends upon file `B`.
4. **Deterministic Risk Scoring:** Mathematical review-risk scoring (0–100) is calculated strictly by SAMAR_3's deterministic formula. Gemini AI is strictly advisory and cannot alter scores.
5. **Path Traversal Protection:** All paths are sanitized, validated against workspace boundaries, and disallowed from escaping sandbox roots.
6. **Isolated Workspaces:** Temporary directories are created with unique UUIDs and guaranteed to be deleted in the orchestrator `finally` block.
