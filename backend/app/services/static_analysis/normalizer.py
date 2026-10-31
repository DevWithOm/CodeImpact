"""Finding normalizer for static analysis results (Knip and jscpd).

Translates raw tool outputs into uniform CodeImpact Finding objects.
"""

from collections import defaultdict
import hashlib
import os
from pathlib import Path
from typing import Any

try:
    from backend.app.schemas.evidence import EvidenceItem
    from backend.app.schemas.finding import Finding
except ImportError:
    from app.schemas.evidence import EvidenceItem
    from app.schemas.finding import Finding


def _generate_finding_id(prefix: str, identity_string: str) -> str:
    """Generates a stable, reproducible finding ID based on content hash."""
    h = hashlib.sha256(identity_string.encode("utf-8")).hexdigest()[:8]
    return f"f_{prefix}_{h}"


def _normalize_path(file_path: str, repo_root: str | None = None) -> str:
    """Converts absolute or OS-specific paths to clean repository-relative POSIX paths.

    Guarantees that absolute host paths are never exposed in user-facing findings.
    """
    if not file_path:
        return ""
    p = Path(file_path)
    if repo_root:
        root_resolved = Path(repo_root).resolve()
        try:
            if p.is_absolute():
                rel = p.resolve().relative_to(root_resolved)
                return rel.as_posix()
            else:
                parts = p.parts
                root_name = root_resolved.name
                if parts and parts[0] == root_name:
                    return Path(*parts[1:]).as_posix()
        except ValueError:
            pass
    # Normalize slashes and strip leading ./
    normalized = file_path.replace("\\", "/").lstrip("./")
    if repo_root:
        root_name = Path(repo_root).name
        if normalized.startswith(f"{root_name}/"):
            normalized = normalized[len(root_name) + 1 :]
    return normalized


def normalize_knip_findings(
    raw_knip_data: dict[str, Any],
    repo_root: str | None = None,
) -> list[Finding]:
    """Transforms raw Knip JSON output into standardized Finding objects.

    Handles Knip 5 `issues` array and legacy top-level keys:
      - files: unused files
      - dependencies / devDependencies: unused package dependencies
      - exports: unused exported symbols
      - types: unused exported types
    """
    findings: list[Finding] = []

    # 1. Unused files (top-level "files" array)
    unused_files = raw_knip_data.get("files", [])
    for file_path in unused_files:
        norm_path = _normalize_path(file_path, repo_root)
        finding_id = _generate_finding_id("uf", norm_path)
        findings.append(
            Finding(
                finding_id=finding_id,
                category="unused_file",
                title="Potentially unused file",
                file_path=norm_path,
                start_line=None,
                end_line=None,
                symbol=None,
                source_tool="knip",
                description="No static import or entry-point reference was found for this file.",
                evidence_class="inconclusive",
                review_risk="unknown",
                evidence=[
                    EvidenceItem(
                        kind="static_reference_scan",
                        status="not_found",
                        source="knip",
                        details="No static reference was found by the configured scan.",
                    )
                ],
                risk_factors=[
                    "File may be referenced dynamically or loaded via configuration."
                ],
                metadata={
                    "knip_issue_type": "files",
                    "original_path": file_path,
                },
            )
        )

    # Helper to process issues from a given container (either top-level or per-file issue)
    def process_issue_item(file_context: str, issue_type: str, item: Any):
        if isinstance(item, dict):
            symbol_name = item.get("name") or item.get("symbol") or item.get("specifier")
            line = item.get("line")
            col = item.get("col")
            target_file = item.get("file") or item.get("path") or file_context
        elif isinstance(item, str):
            symbol_name = item
            line = None
            col = None
            target_file = file_context
        else:
            return

        norm_path = _normalize_path(target_file, repo_root)

        if issue_type in ("dependencies", "devDependencies", "optionalPeerDependencies"):
            finding_id = _generate_finding_id("ud", f"{norm_path}:{symbol_name}")
            findings.append(
                Finding(
                    finding_id=finding_id,
                    category="unused_dependency",
                    title="Potentially unused dependency",
                    file_path=norm_path or "package.json",
                    start_line=int(line) if line is not None else None,
                    end_line=int(line) if line is not None else None,
                    symbol=symbol_name,
                    source_tool="knip",
                    description=f"Dependency '{symbol_name}' listed in {issue_type} has no static import references.",
                    evidence_class="inconclusive",
                    review_risk="unknown",
                    evidence=[
                        EvidenceItem(
                            kind="package_dependency_scan",
                            status="not_found",
                            source="knip",
                            details=f"Dependency '{symbol_name}' was not detected in any static import.",
                            value={"line": line, "col": col},
                        )
                    ],
                    risk_factors=[
                        "Package may be a peer dependency, binary CLI tool, or loaded via plugin config."
                    ],
                    metadata={
                        "knip_issue_type": issue_type,
                        "package_name": symbol_name,
                    },
                )
            )
        elif issue_type in ("exports", "types", "nsExports", "nsTypes", "duplicates"):
            is_type = "type" in issue_type.lower()
            finding_id = _generate_finding_id("ue", f"{norm_path}:{symbol_name}:{line}")
            title = "Potentially unused type export" if is_type else "Potentially unused export"
            findings.append(
                Finding(
                    finding_id=finding_id,
                    category="unused_export",
                    title=title,
                    file_path=norm_path,
                    start_line=int(line) if line is not None else None,
                    end_line=int(line) if line is not None else None,
                    symbol=symbol_name,
                    source_tool="knip",
                    description=(
                        f"Export '{symbol_name}' has no static import reference within the analyzed scope."
                        if symbol_name
                        else "No static reference was found by the configured scan."
                    ),
                    evidence_class="inconclusive",
                    review_risk="unknown",
                    evidence=[
                        EvidenceItem(
                            kind="static_reference_scan",
                            status="not_found",
                            source="knip",
                            details="No direct static reference was returned by this configured scan.",
                            value={"symbol": symbol_name, "line": line, "col": col},
                        )
                    ],
                    risk_factors=[
                        "Symbol may be consumed by external packages, dynamically imported, or used in tests."
                    ],
                    metadata={
                        "knip_issue_type": issue_type,
                        "is_type": is_type,
                    },
                )
            )

    # 2. Check Knip 5 "issues" array
    issues_list = raw_knip_data.get("issues", [])
    for issue_entry in issues_list:
        file_ctx = issue_entry.get("file", "")
        for key in ("dependencies", "devDependencies", "exports", "types", "duplicates", "optionalPeerDependencies"):
            for item in issue_entry.get(key, []):
                process_issue_item(file_ctx, key, item)

    # 3. Check top-level keys (legacy or flat formats)
    for key in ("dependencies", "devDependencies", "exports", "types"):
        for item in raw_knip_data.get(key, []):
            file_ctx = item.get("file", "package.json") if isinstance(item, dict) else "package.json"
            process_issue_item(file_ctx, key, item)

    return findings


def normalize_jscpd_findings(
    raw_jscpd_data: dict[str, Any],
    repo_root: str | None = None,
) -> list[Finding]:
    """Transforms raw jscpd JSON output into standardized Finding objects.

    Groups matching locations for duplicate blocks and preserves all reported coordinates.
    Correctly preserves token counts (including raw 0 counts) without treating 0 as falsy/None.
    """
    duplicates = raw_jscpd_data.get("duplicates", [])
    if not duplicates:
        return []

    groups: list[dict[str, Any]] = []

    for dup in duplicates:
        first_file = dup.get("firstFile", {})
        second_file = dup.get("secondFile", {})

        first_path = _normalize_path(first_file.get("name") or "", repo_root)
        second_path = _normalize_path(second_file.get("name") or "", repo_root)

        first_start = first_file.get("start") or first_file.get("startLoc", {}).get("line")
        first_end = first_file.get("end") or first_file.get("endLoc", {}).get("line")

        second_start = second_file.get("start") or second_file.get("startLoc", {}).get("line")
        second_end = second_file.get("end") or second_file.get("endLoc", {}).get("line")

        loc1 = (first_path, int(first_start) if first_start is not None else None, int(first_end) if first_end is not None else None)
        loc2 = (second_path, int(second_start) if second_start is not None else None, int(second_end) if second_end is not None else None)

        lines_count = dup.get("lines")
        tokens_count = dup.get("tokens")  # Numeric value from jscpd (e.g. 0 or 144)
        fragment = dup.get("fragment", "")
        format_name = dup.get("format", "unknown")

        merged = False
        for grp in groups:
            if (fragment and grp["fragment"] == fragment) or (loc1 in grp["locations"] or loc2 in grp["locations"]):
                grp["locations"].add(loc1)
                grp["locations"].add(loc2)
                if not grp["fragment"] and fragment:
                    grp["fragment"] = fragment
                if lines_count is not None:
                    grp["lines"] = lines_count
                if tokens_count is not None:
                    grp["tokens"] = tokens_count
                merged = True
                break

        if not merged:
            groups.append({
                "locations": {loc1, loc2},
                "lines": lines_count,
                "tokens": tokens_count,
                "fragment": fragment,
                "format": format_name,
            })

    findings: list[Finding] = []

    for grp in groups:
        sorted_locs = sorted(
            list(grp["locations"]),
            key=lambda x: (x[0], x[1] if x[1] is not None else -1)
        )
        if not sorted_locs:
            continue

        primary = sorted_locs[0]
        primary_path, primary_start, primary_end = primary
        other_locs = sorted_locs[1:]

        dup_id_key = f"{primary_path}:{primary_start}:{len(other_locs)}:{other_locs[0][0] if other_locs else ''}"
        finding_id = _generate_finding_id("dup", dup_id_key)

        matching_paths = [l[0] for l in other_locs]
        matching_str = ", ".join(matching_paths)
        lines_label = f"{grp['lines']} lines" if grp["lines"] is not None else "matching code"
        tokens_label = f", {grp['tokens']} tokens" if grp["tokens"] is not None and grp["tokens"] > 0 else ""

        other_locations_meta = [
            {
                "file_path": l[0],
                "start_line": l[1],
                "end_line": l[2],
            }
            for l in other_locs
        ]

        desc = (
            f"Duplicate code block ({lines_label}{tokens_label}) also found in {len(other_locs)} other location(s): {matching_str}."
            if other_locs
            else f"Duplicate code block ({lines_label}) detected."
        )

        findings.append(
            Finding(
                finding_id=finding_id,
                category="duplicate_code",
                title="Duplicate code block",
                file_path=primary_path,
                start_line=primary_start,
                end_line=primary_end,
                symbol=None,
                source_tool="jscpd",
                description=desc,
                evidence_class="strong",
                review_risk="unknown",
                evidence=[
                    EvidenceItem(
                        kind="duplicate_block",
                        status="found",
                        source="jscpd",
                        details=f"Identical or near-identical code lines detected across {len(sorted_locs)} locations.",
                        value={
                            "duplicate_lines": grp["lines"],
                            "tokens": grp["tokens"],  # Preserves raw value (0 or actual count)
                            "format": grp["format"],
                            "matching_location_count": len(other_locs),
                        },
                    )
                ],
                risk_factors=[
                    "Duplicated logic increases maintenance overhead and risk of inconsistent updates."
                ],
                metadata={
                    "format": grp["format"],
                    "duplicate_locations": other_locations_meta,
                    "duplicate_lines": grp["lines"],
                    "tokens": grp["tokens"],  # Preserves raw value without falsy None conversion
                    "fragment_preview": grp["fragment"][:200] if grp["fragment"] else None,
                    "duplicate_group_size": len(sorted_locs),
                },
            )
        )

    findings.sort(key=lambda f: (f.file_path, f.start_line if f.start_line is not None else 0))
    return findings
