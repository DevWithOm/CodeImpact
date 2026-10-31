"""Static code analysis services module (Knip, jscpd, and analysis orchestration)."""

try:
    from backend.app.services.static_analysis.analyzer import (
        analyze_repository,
        cleanup_workspace,
        retrieve_repository,
    )
    from backend.app.services.static_analysis.jscpd_runner import (
        get_jscpd_version,
        run_jscpd,
        run_jscpd_analysis,
    )
    from backend.app.services.static_analysis.knip_runner import (
        get_knip_version,
        run_knip,
        run_knip_analysis,
    )
except ImportError:
    from app.services.static_analysis.analyzer import (
        analyze_repository,
        cleanup_workspace,
        retrieve_repository,
    )
    from app.services.static_analysis.jscpd_runner import (
        get_jscpd_version,
        run_jscpd,
        run_jscpd_analysis,
    )
    from app.services.static_analysis.knip_runner import (
        get_knip_version,
        run_knip,
        run_knip_analysis,
    )

__all__ = [
    "analyze_repository",
    "retrieve_repository",
    "cleanup_workspace",
    "run_knip",
    "run_knip_analysis",
    "get_knip_version",
    "run_jscpd",
    "run_jscpd_analysis",
    "get_jscpd_version",
]

