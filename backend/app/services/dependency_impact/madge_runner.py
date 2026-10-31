"""Madge subprocess runner for CodeImpact Dependency & Impact Engine.

Executes Madge safely to extract dependency maps and circular dependencies
from JavaScript/TypeScript repositories. Features in-flight bounded output
streaming memory protection and direct Node.js execution with shell=False.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Maximum stdout/stderr bytes to capture in-flight per stream (5MB)
MAX_OUTPUT_BYTES = 5 * 1024 * 1024

# Canonical Statuses
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_UNAVAILABLE = "unavailable"

# Canonical Error Codes
ERR_MADGE_NOT_FOUND = "MADGE_NOT_FOUND"
ERR_MADGE_EXECUTION_FAILED = "MADGE_EXECUTION_FAILED"
ERR_MADGE_TIMEOUT = "MADGE_TIMEOUT"
ERR_MADGE_INVALID_JSON = "MADGE_INVALID_JSON"
ERR_MADGE_OUTPUT_LIMIT_EXCEEDED = "MADGE_OUTPUT_LIMIT_EXCEEDED"
ERR_REPOSITORY_PATH_INVALID = "REPOSITORY_PATH_INVALID"
ERR_REPOSITORY_NOT_FOUND = "REPOSITORY_NOT_FOUND"
ERR_MADGE_PARTIAL_OUTPUT = "MADGE_PARTIAL_OUTPUT"


def normalize_repo_relative_path(path_str: str) -> str | None:
    """Normalize a module path to a repository-relative POSIX path.

    Rejects paths that escape the root or contain invalid traversal.

    Args:
        path_str: Raw file path from tool output.

    Returns:
        Normalized POSIX path (e.g. 'src/app.ts') or None if path is unsafe/invalid.
    """
    if not path_str or not isinstance(path_str, str):
        return None

    cleaned = path_str.strip().replace("\\", "/")

    # Reject absolute drive paths on Windows (e.g. C:/...) or root paths (/...)
    if re.match(r"^[a-zA-Z]:", cleaned) or cleaned.startswith("/"):
        return None

    # Strip leading ./
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]

    parts = cleaned.split("/")
    # Check for path traversal segments
    if ".." in parts:
        return None

    # Filter empty segments
    filtered = [p for p in parts if p and p != "."]
    if not filtered:
        return None

    return "/".join(filtered)


def sanitize_message(msg: str, repo_path: str | None = None) -> str:
    """Sanitize error messages to remove host machine paths and secrets.

    Args:
        msg: Raw message string.
        repo_path: Optional repository path to scrub specifically.

    Returns:
        Sanitized message string.
    """
    if not msg:
        return ""

    sanitized = str(msg)
    if repo_path:
        sanitized = sanitized.replace(str(repo_path), "<repo_root>")
        sanitized = sanitized.replace(str(repo_path).replace("\\", "/"), "<repo_root>")

    # Scrub standard Windows absolute path patterns
    sanitized = re.sub(r"[a-zA-Z]:\\[^:\n\r\t]+", "<path>", sanitized)
    sanitized = re.sub(r"[a-zA-Z]:/[^:\n\r\t]+", "<path>", sanitized)
    # Scrub common unix home paths
    sanitized = re.sub(r"/home/[^/\s]+", "<path>", sanitized)
    sanitized = re.sub(r"/Users/[^/\s]+", "<path>", sanitized)

    return sanitized.strip()


def find_node_executable() -> str | None:
    """Locate the Node.js executable on the host system.

    Returns:
        Path to node binary or None if unavailable.
    """
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        candidate = shutil.which("node.exe") or shutil.which("node")
        if candidate:
            return candidate

    return shutil.which("node")


def find_madge_entrypoint() -> str | None:
    """Locate the Madge JavaScript CLI entry point script.

    Finds tooling/node_modules/madge/bin/cli.js relative to project.

    Returns:
        Path to cli.js string or None if not found.
    """
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        candidate_entry = parent / "tooling" / "node_modules" / "madge" / "bin" / "cli.js"
        if candidate_entry.is_file():
            return str(candidate_entry)
    return None


def find_madge_executable() -> str | None:
    """Locate the Madge executable or entry point.

    Priority:
    1. Project-local Madge JS entrypoint (tooling/node_modules/madge/bin/cli.js)
       if node is available, OR local bin (tooling/node_modules/.bin/madge[.cmd])
    2. Global madge on PATH

    Returns:
        Path to executable / script string or None if unavailable.
    """
    is_windows = platform.system().lower() == "windows"
    bin_name = "madge.cmd" if is_windows else "madge"

    # Search for project tooling directory relative to this file
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        cli_js = parent / "tooling" / "node_modules" / "madge" / "bin" / "cli.js"
        candidate_bin = parent / "tooling" / "node_modules" / ".bin" / bin_name
        alt_bin = parent / "tooling" / "node_modules" / ".bin" / "madge"

        if cli_js.is_file():
            return str(cli_js)
        if candidate_bin.is_file():
            return str(candidate_bin)
        if alt_bin.is_file():
            return str(alt_bin)

    # Priority 2: Global PATH
    if is_windows:
        cmd_path = shutil.which("madge.cmd")
        if cmd_path:
            return cmd_path

    global_path = shutil.which("madge")
    if global_path:
        return global_path

    return None


def resolve_madge_command(madge_bin: str | None = None) -> list[str] | None:
    """Resolve the command argument list for invoking Madge safely.

    On Windows and POSIX, if the target is a JS file (like cli.js) or a local
    Madge install, executes via Node directly with shell=False.

    Args:
        madge_bin: Optional explicit executable or script path.

    Returns:
        Command list (e.g. ['node', '.../cli.js']) or None if unavailable.
    """
    entrypoint = madge_bin or find_madge_executable()
    if not entrypoint:
        return None

    node_bin = find_node_executable()

    # Case A: Explicit or discovered JavaScript entrypoint
    if entrypoint.endswith(".js"):
        if node_bin:
            return [node_bin, entrypoint]
        return None

    # Case B: Local .bin/madge.cmd or .bin/madge -> Prefer node + cli.js if available
    local_cli = find_madge_entrypoint()
    if local_cli and node_bin:
        return [node_bin, local_cli]

    # Case C: Global or explicit executable binary
    return [entrypoint]


def get_madge_version(madge_bin: str | None = None) -> str | None:
    """Retrieve the installed Madge version string.

    Args:
        madge_bin: Optional explicit executable path.

    Returns:
        Version string (e.g. '8.0.0') or None if failed.
    """
    cmd = resolve_madge_command(madge_bin)
    if not cmd:
        return None

    try:
        proc = subprocess.run(
            cmd + ["--version"],
            capture_output=True,
            text=True,
            shell=False,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception as e:
        logger.debug("Failed to retrieve Madge version: %s", e)

    return None


def _validate_repo_path(repo_path: str) -> tuple[Path | None, dict | None]:
    """Validate that repository path is non-empty, exists, and is a directory.

    Returns:
        Tuple of (resolved_path, error_dict)
    """
    if not repo_path or not isinstance(repo_path, str) or not repo_path.strip():
        return None, {
            "code": ERR_REPOSITORY_PATH_INVALID,
            "message": "Repository path must be a non-empty string.",
            "retryable": False,
        }

    try:
        p = Path(repo_path).resolve()
    except Exception as e:
        return None, {
            "code": ERR_REPOSITORY_PATH_INVALID,
            "message": f"Invalid repository path format: {sanitize_message(str(e))}",
            "retryable": False,
        }

    if not p.exists():
        return None, {
            "code": ERR_REPOSITORY_NOT_FOUND,
            "message": "Repository path does not exist on disk.",
            "retryable": False,
        }

    if not p.is_dir():
        return None, {
            "code": ERR_REPOSITORY_PATH_INVALID,
            "message": "Repository path is not a directory.",
            "retryable": False,
        }

    return p, None


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Terminate and kill a subprocess cleanly to prevent zombies."""
    try:
        proc.terminate()
        proc.wait(timeout=1.0)
    except (subprocess.TimeoutExpired, OSError):
        try:
            proc.kill()
            proc.wait(timeout=1.0)
        except OSError:
            pass


def run_subprocess_bounded(
    cmd: list[str],
    cwd: str,
    timeout_seconds: float = 30.0,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> tuple[int | None, str, str, bool, bool]:
    """Execute a subprocess with strict in-flight memory bounds and timeout.

    Reads stdout and stderr concurrently in streaming reader threads.
    If either stream exceeds max_output_bytes, execution is immediately
    terminated to protect host memory.

    Args:
        cmd: Argument list for subprocess.
        cwd: Working directory.
        timeout_seconds: Execution deadline in seconds.
        max_output_bytes: Maximum allowed bytes per stream (default 5MB).

    Returns:
        Tuple of (returncode, stdout_str, stderr_str, timed_out, overflowed)
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )

    stdout_buf = bytearray()
    stderr_buf = bytearray()
    overflow_event = threading.Event()
    stop_event = threading.Event()

    def stream_reader(pipe, buffer: bytearray) -> None:
        try:
            while not stop_event.is_set():
                chunk = pipe.read(65536)
                if not chunk:
                    break
                if len(buffer) + len(chunk) > max_output_bytes:
                    remaining = max_output_bytes - len(buffer)
                    if remaining > 0:
                        buffer.extend(chunk[:remaining])
                    overflow_event.set()
                    break
                buffer.extend(chunk)
        except Exception:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    t_stdout = threading.Thread(target=stream_reader, args=(proc.stdout, stdout_buf), daemon=True)
    t_stderr = threading.Thread(target=stream_reader, args=(proc.stderr, stderr_buf), daemon=True)
    t_stdout.start()
    t_stderr.start()

    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    overflowed = False

    while True:
        if overflow_event.is_set():
            overflowed = True
            _kill_process_tree(proc)
            break
        if proc.poll() is not None:
            break
        if time.monotonic() > deadline:
            timed_out = True
            _kill_process_tree(proc)
            break
        time.sleep(0.01)

    stop_event.set()
    t_stdout.join(timeout=1.0)
    t_stderr.join(timeout=1.0)

    # Ensure process is completely finished
    try:
        proc.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)

    stdout_str = stdout_buf.decode("utf-8", errors="replace")
    stderr_str = stderr_buf.decode("utf-8", errors="replace")

    return (proc.returncode, stdout_str, stderr_str, timed_out, overflowed)


def get_dependency_map(
    repo_path: str,
    timeout_seconds: int = 30,
    madge_bin: str | None = None,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> dict[str, Any]:
    """Extract raw dependency map from repository using Madge.

    Args:
        repo_path: Absolute local path to repository root.
        timeout_seconds: Subprocess timeout in seconds (default 30).
        madge_bin: Optional explicit path to madge binary or entrypoint.
        max_output_bytes: In-flight stream limit (default 5MB).

    Returns:
        Dictionary with status, dependency_map, error, and warnings.
    """
    path_obj, path_err = _validate_repo_path(repo_path)
    if path_err:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": path_err,
            "warnings": [],
        }

    cmd_prefix = resolve_madge_command(madge_bin)
    if not cmd_prefix:
        return {
            "status": STATUS_UNAVAILABLE,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_NOT_FOUND,
                "message": "Madge executable or Node.js runtime is unavailable.",
                "retryable": False,
            },
            "warnings": [],
        }

    cmd = cmd_prefix + [
        "--extensions",
        "ts,tsx,js,jsx",
        "--json",
        ".",
    ]

    try:
        retcode, stdout_str, stderr_str, timed_out, overflowed = run_subprocess_bounded(
            cmd,
            cwd=str(path_obj),
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
    except Exception as e:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_EXECUTION_FAILED,
                "message": f"Failed to execute Madge: {sanitize_message(str(e), str(path_obj))}",
                "retryable": False,
            },
            "warnings": [],
        }

    if overflowed:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_OUTPUT_LIMIT_EXCEEDED,
                "message": f"Madge output stream exceeded maximum allowed limit of {max_output_bytes} bytes.",
                "retryable": False,
            },
            "warnings": [],
        }

    if timed_out:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_TIMEOUT,
                "message": f"Madge dependency extraction timed out after {timeout_seconds} seconds.",
                "retryable": True,
            },
            "warnings": [],
        }

    if retcode != 0:
        err_msg = stderr_str.strip() or stdout_str.strip() or "Madge returned a non-zero exit code."
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_EXECUTION_FAILED,
                "message": sanitize_message(err_msg, str(path_obj)),
                "retryable": False,
            },
            "warnings": [],
        }

    try:
        parsed_json = json.loads(stdout_str)
    except Exception as e:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_INVALID_JSON,
                "message": f"Madge output was not valid JSON: {sanitize_message(str(e))}",
                "retryable": False,
            },
            "warnings": [],
        }

    if not isinstance(parsed_json, dict):
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "error": {
                "code": ERR_MADGE_INVALID_JSON,
                "message": "Madge JSON root must be an object/dictionary.",
                "retryable": False,
            },
            "warnings": [],
        }

    normalized_map: dict[str, list[str]] = {}
    warnings: list[dict[str, str]] = []

    for raw_src, raw_deps in parsed_json.items():
        norm_src = normalize_repo_relative_path(raw_src)
        if not norm_src:
            warnings.append({
                "code": "UNSAFE_PATH_SKIPPED",
                "message": f"Skipped source path with invalid format or traversal: {raw_src}",
            })
            continue

        if not isinstance(raw_deps, list):
            warnings.append({
                "code": "INVALID_DEPENDENCY_LIST",
                "message": f"Dependencies for '{norm_src}' must be a list; skipped.",
            })
            continue

        valid_deps: list[str] = []
        for dep in raw_deps:
            norm_dep = normalize_repo_relative_path(dep)
            if norm_dep:
                if norm_dep not in valid_deps:
                    valid_deps.append(norm_dep)
            else:
                warnings.append({
                    "code": "UNSAFE_PATH_SKIPPED",
                    "message": f"Skipped dependency with invalid format: {dep}",
                })

        normalized_map[norm_src] = valid_deps

    return {
        "status": STATUS_SUCCESS,
        "dependency_map": normalized_map,
        "error": None,
        "warnings": warnings,
    }


def get_circular_dependencies(
    repo_path: str,
    timeout_seconds: int = 30,
    madge_bin: str | None = None,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> dict[str, Any]:
    """Extract circular dependency chains using Madge.

    Note on Madge behavior: When circular dependencies exist, Madge exits
    with code 1 while outputting a valid JSON cycles array.

    Args:
        repo_path: Absolute local path to repository root.
        timeout_seconds: Subprocess timeout in seconds.
        madge_bin: Optional explicit path to madge binary or entrypoint.
        max_output_bytes: In-flight stream limit (default 5MB).

    Returns:
        Dictionary with status, cycles, error, and warnings.
    """
    path_obj, path_err = _validate_repo_path(repo_path)
    if path_err:
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": path_err,
            "warnings": [],
        }

    cmd_prefix = resolve_madge_command(madge_bin)
    if not cmd_prefix:
        return {
            "status": STATUS_UNAVAILABLE,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_NOT_FOUND,
                "message": "Madge executable or Node.js runtime is unavailable.",
                "retryable": False,
            },
            "warnings": [],
        }

    cmd = cmd_prefix + [
        "--extensions",
        "ts,tsx,js,jsx",
        "--circular",
        "--json",
        ".",
    ]

    try:
        retcode, stdout_str, stderr_str, timed_out, overflowed = run_subprocess_bounded(
            cmd,
            cwd=str(path_obj),
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
    except Exception as e:
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_EXECUTION_FAILED,
                "message": f"Failed to execute circular extraction: {sanitize_message(str(e), str(path_obj))}",
                "retryable": False,
            },
            "warnings": [],
        }

    if overflowed:
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_OUTPUT_LIMIT_EXCEEDED,
                "message": f"Madge circular output stream exceeded maximum allowed limit of {max_output_bytes} bytes.",
                "retryable": False,
            },
            "warnings": [],
        }

    if timed_out:
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_TIMEOUT,
                "message": f"Circular dependency extraction timed out after {timeout_seconds} seconds.",
                "retryable": True,
            },
            "warnings": [],
        }

    # In Madge, exit code 0 (no cycles) or code 1 (cycles found) are valid output states
    try:
        parsed_cycles = json.loads(stdout_str)
    except Exception:
        if retcode != 0:
            err_msg = stderr_str.strip() or stdout_str.strip() or "Madge circular analysis failed."
            return {
                "status": STATUS_FAILED,
                "cycles": None,
                "error": {
                    "code": ERR_MADGE_EXECUTION_FAILED,
                    "message": sanitize_message(err_msg, str(path_obj)),
                    "retryable": False,
                },
                "warnings": [],
            }
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_INVALID_JSON,
                "message": "Madge circular output was not valid JSON.",
                "retryable": False,
            },
            "warnings": [],
        }

    if not isinstance(parsed_cycles, list):
        return {
            "status": STATUS_FAILED,
            "cycles": None,
            "error": {
                "code": ERR_MADGE_INVALID_JSON,
                "message": "Madge circular output root must be a list/array.",
                "retryable": False,
            },
            "warnings": [],
        }

    normalized_cycles: list[list[str]] = []
    warnings: list[dict[str, str]] = []

    for raw_cycle in parsed_cycles:
        if not isinstance(raw_cycle, list):
            warnings.append({
                "code": "INVALID_CYCLE_ENTRY",
                "message": "Non-list item found in cycles output; skipped.",
            })
            continue

        normalized_chain: list[str] = []
        for p in raw_cycle:
            norm_p = normalize_repo_relative_path(p)
            if norm_p:
                normalized_chain.append(norm_p)

        if len(normalized_chain) >= 2:
            normalized_cycles.append(normalized_chain)

    return {
        "status": STATUS_SUCCESS,
        "cycles": normalized_cycles,
        "error": None,
        "warnings": warnings,
    }


def run_madge(
    repo_path: str,
    timeout_seconds: int = 30,
    madge_bin: str | None = None,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> dict[str, Any]:
    """Execute complete Madge dependency analysis on a repository workspace.

    Extracts dependency map and circular dependencies, combining them into
    a unified result conforming to the CodeImpact Phase 2 contract.

    Args:
        repo_path: Absolute local path to repository workspace.
        timeout_seconds: Subprocess timeout in seconds.
        madge_bin: Optional explicit path to madge binary or entrypoint.
        max_output_bytes: In-flight stream limit (default 5MB).

    Returns:
        Structured result conforming to canonical contract.
    """
    start_time = time.perf_counter()

    executable = madge_bin or find_madge_executable()
    version = get_madge_version(executable) if executable else None

    # Step 1: Extract dependency map
    dep_result = get_dependency_map(
        repo_path,
        timeout_seconds=timeout_seconds,
        madge_bin=executable,
        max_output_bytes=max_output_bytes,
    )
    if dep_result["status"] == STATUS_UNAVAILABLE:
        return {
            "status": STATUS_UNAVAILABLE,
            "dependency_map": None,
            "cycles": None,
            "error": dep_result["error"],
            "warnings": [],
            "metadata": {
                "madge_version": version,
                "execution_time_ms": int((time.perf_counter() - start_time) * 1000),
                "dependency_map_available": False,
                "cycles_available": False,
            },
        }

    if dep_result["status"] == STATUS_FAILED:
        return {
            "status": STATUS_FAILED,
            "dependency_map": None,
            "cycles": None,
            "error": dep_result["error"],
            "warnings": dep_result.get("warnings", []),
            "metadata": {
                "madge_version": version,
                "execution_time_ms": int((time.perf_counter() - start_time) * 1000),
                "dependency_map_available": False,
                "cycles_available": False,
            },
        }

    # Step 2: Extract circular dependencies
    circ_result = get_circular_dependencies(
        repo_path,
        timeout_seconds=timeout_seconds,
        madge_bin=executable,
        max_output_bytes=max_output_bytes,
    )

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    all_warnings = list(dep_result.get("warnings", []))

    # If circular extraction failed but dependency map succeeded -> Partial status
    if circ_result["status"] != STATUS_SUCCESS:
        all_warnings.append({
            "code": ERR_MADGE_PARTIAL_OUTPUT,
            "message": f"Circular dependency extraction was unsuccessful: {circ_result.get('error', {}).get('message', 'Unknown error')}",
        })
        return {
            "status": STATUS_PARTIAL,
            "dependency_map": dep_result["dependency_map"],
            "cycles": None,
            "error": None,
            "warnings": all_warnings,
            "metadata": {
                "madge_version": version,
                "execution_time_ms": elapsed_ms,
                "dependency_map_available": True,
                "cycles_available": False,
            },
        }

    all_warnings.extend(circ_result.get("warnings", []))

    return {
        "status": STATUS_SUCCESS,
        "dependency_map": dep_result["dependency_map"],
        "cycles": circ_result["cycles"],
        "error": None,
        "warnings": all_warnings,
        "metadata": {
            "madge_version": version,
            "execution_time_ms": elapsed_ms,
            "dependency_map_available": True,
            "cycles_available": True,
        },
    }
