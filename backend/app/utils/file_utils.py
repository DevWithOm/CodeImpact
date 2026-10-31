"""File utility functions for CodeImpact.

Handles path traversal protection, repository size checks, file filtering,
and language detection.
"""

import os
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    "coverage",
    ".cache",
    ".codeimpact",
}

JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
SUPPORTED_EXTENSIONS = JS_EXTENSIONS | TS_EXTENSIONS


def normalize_relative_path(path_str: str, base_dir: str | None = None) -> str:
    """Normalizes a file path to POSIX style relative to base_dir if provided."""
    if not path_str:
        return ""
    p = Path(path_str)
    if base_dir and p.is_absolute():
        try:
            return p.resolve().relative_to(Path(base_dir).resolve()).as_posix()
        except ValueError:
            pass
    return p.as_posix()


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Verifies that target_path resides within base_dir to prevent path traversal.

    Args:
        base_dir: The allowed boundary directory.
        target_path: The path to validate.

    Returns:
        True if target_path is within base_dir, False otherwise.
    """
    try:
        base = os.path.realpath(os.path.abspath(base_dir))
        target = os.path.realpath(os.path.abspath(target_path))
        return os.path.commonpath([base, target]) == base
    except (ValueError, OSError):
        return False


def get_directory_size_mb(path: str) -> float:
    """Computes total directory size in megabytes, ignoring errors on unreadable files."""
    total_bytes = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                try:
                    total_bytes += entry.stat().st_size
                except OSError:
                    pass
            elif entry.is_dir(follow_symlinks=False):
                if entry.name not in IGNORED_DIRECTORIES:
                    total_bytes += int(get_directory_size_mb(entry.path) * 1024 * 1024)
    except OSError:
        pass
    return round(total_bytes / (1024 * 1024), 2)


def scan_repository_files(
    repo_path: str,
    max_files: int = 10000,
) -> dict:
    """Scans repository files and detects eligible JS/TS files and languages.

    Returns a dict with:
        eligible_file_count: Total JS/TS files
        total_file_count: All non-ignored files
        languages: List of detected languages (e.g. ['TypeScript', 'JavaScript'])
        has_package_json: bool
        files: List of relative paths for eligible files
    """
    eligible_files: list[str] = []
    total_count = 0
    languages: set[str] = set()
    has_package_json = False

    repo_path_obj = Path(repo_path).resolve()

    for root, dirs, files in os.walk(repo_path_obj):
        # Exclude ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]

        for file_name in files:
            total_count += 1
            if total_count > max_files:
                break

            file_path = Path(root) / file_name
            rel_path = file_path.relative_to(repo_path_obj).as_posix()

            if file_name == "package.json":
                has_package_json = True

            ext = file_path.suffix.lower()
            if ext in TS_EXTENSIONS:
                languages.add("TypeScript")
                eligible_files.append(rel_path)
            elif ext in JS_EXTENSIONS:
                languages.add("JavaScript")
                eligible_files.append(rel_path)

    # Sort languages predictably
    sorted_languages = sorted(list(languages))

    return {
        "eligible_file_count": len(eligible_files),
        "total_file_count": total_count,
        "languages": sorted_languages,
        "has_package_json": has_package_json,
        "files": eligible_files,
    }
