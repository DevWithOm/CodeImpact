"""Static application and package entry-point detection engine for CodeImpact.

Identifies potential entry points in JavaScript/TypeScript repositories using
package metadata (main, module, exports, bin) and conventional filenames.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.app.services.dependency_impact.madge_runner import normalize_repo_relative_path

logger = logging.getLogger(__name__)

# Canonical entry-point filename patterns
COMMON_ENTRY_FILENAMES = {
    "src/index.ts",
    "src/index.tsx",
    "src/index.js",
    "src/index.jsx",
    "index.ts",
    "index.js",
    "src/main.ts",
    "src/main.tsx",
    "src/main.js",
    "src/main.jsx",
    "main.ts",
    "main.js",
    "src/app.ts",
    "src/app.tsx",
    "src/app.js",
    "src/App.tsx",
    "src/App.jsx",
    "app.ts",
    "app.js",
    "server.ts",
    "server.js",
    "src/server.ts",
    "src/server.js",
}


def read_json_safely(file_path: Path) -> dict[str, Any]:
    """Read a JSON file safely without throwing exceptions on malformed content."""
    try:
        if file_path.exists() and file_path.is_file():
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.debug("Could not parse JSON from %s: %s", file_path, e)
    return {}


def detect_entry_points(
    repo_path: str | Path | None = None,
    graph_nodes: list[str] | set[str] | list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Statically detect application entry points from package metadata and source files.

    Args:
        repo_path: Absolute local path to repository workspace.
        graph_nodes: Optional list or set of known graph nodes.

    Returns:
        List of entry point dictionaries conforming to EntryPointEvidence schema.
    """
    entry_points_by_path: dict[str, dict[str, Any]] = {}

    path_obj = Path(repo_path).resolve() if repo_path else None

    # Collect known file paths in repository
    known_nodes: set[str] = set()
    if graph_nodes:
        for item in graph_nodes:
            p = item if isinstance(item, str) else (item.get("file_path") or item.get("id"))
            if p:
                norm = normalize_repo_relative_path(p)
                if norm:
                    known_nodes.add(norm)

    # 1. Inspect package.json if repo_path is provided
    if path_obj and path_obj.exists() and path_obj.is_dir():
        pkg_json_path = path_obj / "package.json"
        pkg_data = read_json_safely(pkg_json_path) if pkg_json_path.exists() else {}

        if pkg_data:
            # Check 'main'
            main_field = pkg_data.get("main")
            if main_field and isinstance(main_field, str):
                norm_main = normalize_repo_relative_path(main_field)
                if norm_main:
                    entry_points_by_path[norm_main] = {
                        "file_path": norm_main,
                        "entry_point_status": "found",
                        "entry_point_type": "package_main",
                        "evidence": [
                            {
                                "kind": "package_configuration",
                                "source": "package.json",
                                "details": f"Declared in 'main' field: '{main_field}'",
                            }
                        ],
                    }

            # Check 'module'
            module_field = pkg_data.get("module")
            if module_field and isinstance(module_field, str):
                norm_mod = normalize_repo_relative_path(module_field)
                if norm_mod:
                    if norm_mod in entry_points_by_path:
                        entry_points_by_path[norm_mod]["evidence"].append({
                            "kind": "package_configuration",
                            "source": "package.json",
                            "details": f"Declared in 'module' field: '{module_field}'",
                        })
                    else:
                        entry_points_by_path[norm_mod] = {
                            "file_path": norm_mod,
                            "entry_point_status": "found",
                            "entry_point_type": "package_module",
                            "evidence": [
                                {
                                    "kind": "package_configuration",
                                    "source": "package.json",
                                    "details": f"Declared in 'module' field: '{module_field}'",
                                }
                            ],
                        }

            # Check 'bin'
            bin_field = pkg_data.get("bin")
            if isinstance(bin_field, str):
                norm_bin = normalize_repo_relative_path(bin_field)
                if norm_bin:
                    entry_points_by_path[norm_bin] = {
                        "file_path": norm_bin,
                        "entry_point_status": "found",
                        "entry_point_type": "cli_bin",
                        "evidence": [
                            {
                                "kind": "package_configuration",
                                "source": "package.json",
                                "details": f"Declared in 'bin' executable: '{bin_field}'",
                            }
                        ],
                    }
            elif isinstance(bin_field, dict):
                for bin_name, bin_target in bin_field.items():
                    if isinstance(bin_target, str):
                        norm_bin = normalize_repo_relative_path(bin_target)
                        if norm_bin:
                            entry_points_by_path[norm_bin] = {
                                "file_path": norm_bin,
                                "entry_point_status": "found",
                                "entry_point_type": "cli_bin",
                                "evidence": [
                                    {
                                        "kind": "package_configuration",
                                        "source": "package.json",
                                        "details": f"Declared in 'bin.{bin_name}': '{bin_target}'",
                                    }
                                ],
                            }

            # Check 'exports' (simple string or dict)
            exports_field = pkg_data.get("exports")
            if isinstance(exports_field, str):
                norm_exp = normalize_repo_relative_path(exports_field)
                if norm_exp and norm_exp not in entry_points_by_path:
                    entry_points_by_path[norm_exp] = {
                        "file_path": norm_exp,
                        "entry_point_status": "found",
                        "entry_point_type": "package_export",
                        "evidence": [
                            {
                                "kind": "package_configuration",
                                "source": "package.json",
                                "details": f"Declared in 'exports': '{exports_field}'",
                            }
                        ],
                    }
            elif isinstance(exports_field, dict):
                for exp_key, exp_target in exports_field.items():
                    target_str = exp_target if isinstance(exp_target, str) else (
                        exp_target.get("import") or exp_target.get("default") if isinstance(exp_target, dict) else None
                    )
                    if target_str and isinstance(target_str, str):
                        norm_exp = normalize_repo_relative_path(target_str)
                        if norm_exp:
                            if norm_exp in entry_points_by_path:
                                entry_points_by_path[norm_exp]["evidence"].append({
                                    "kind": "package_configuration",
                                    "source": "package.json",
                                    "details": f"Declared in 'exports.{exp_key}': '{target_str}'",
                                })
                            else:
                                entry_points_by_path[norm_exp] = {
                                    "file_path": norm_exp,
                                    "entry_point_status": "found",
                                    "entry_point_type": "package_export",
                                    "evidence": [
                                        {
                                            "kind": "package_configuration",
                                            "source": "package.json",
                                            "details": f"Declared in 'exports.{exp_key}': '{target_str}'",
                                        }
                                    ],
                                }

    # 2. Check canonical application entry points in known graph nodes or filesystem
    all_candidates = set(known_nodes)
    if path_obj and path_obj.exists() and path_obj.is_dir():
        for common_path in COMMON_ENTRY_FILENAMES:
            if (path_obj / common_path).exists():
                all_candidates.add(common_path)

    for cand in all_candidates:
        if cand in COMMON_ENTRY_FILENAMES and cand not in entry_points_by_path:
            entry_points_by_path[cand] = {
                "file_path": cand,
                "entry_point_status": "found",
                "entry_point_type": "application_entry",
                "evidence": [
                    {
                        "kind": "filename_convention",
                        "source": "convention",
                        "details": f"Matches standard application entry convention: '{cand}'",
                    }
                ],
            }

    # Sort deterministically
    return [entry_points_by_path[p] for p in sorted(entry_points_by_path.keys())]

