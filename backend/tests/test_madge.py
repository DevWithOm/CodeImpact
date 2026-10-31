"""Comprehensive unit and regression tests for CodeImpact Madge Subprocess Runner.

Covers:
- All 15 original Phase 2 tests (preserved and hardened)
- 10 Subprocess output limits & streaming memory protection tests
- 10 Windows compatibility, space-in-path, and Node.js execution tests
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.dependency_impact.madge_runner import (
    ERR_MADGE_EXECUTION_FAILED,
    ERR_MADGE_INVALID_JSON,
    ERR_MADGE_NOT_FOUND,
    ERR_MADGE_OUTPUT_LIMIT_EXCEEDED,
    ERR_MADGE_PARTIAL_OUTPUT,
    ERR_MADGE_TIMEOUT,
    ERR_REPOSITORY_NOT_FOUND,
    ERR_REPOSITORY_PATH_INVALID,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    find_madge_entrypoint,
    find_madge_executable,
    find_node_executable,
    get_circular_dependencies,
    get_dependency_map,
    get_madge_version,
    normalize_repo_relative_path,
    resolve_madge_command,
    run_madge,
    run_subprocess_bounded,
    sanitize_message,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "dependency_fixture"


# ==============================================================================
# SECTION 1: ORIGINAL 15 TESTS (PRESERVED & HARDENED)
# ==============================================================================

# Test 1: Executable discovery
def test_executable_discovery():
    """Verify that local tooling Madge executable or JS entrypoint is discovered."""
    exe = find_madge_executable()
    assert exe is not None, "Madge executable or entry point should be discovered in tooling"
    assert Path(exe).exists(), f"Discovered executable {exe} must exist on disk"
    version = get_madge_version(exe)
    assert version == "8.0.0", f"Discovered Madge version should be 8.0.0, got {version}"


# Test 2: Missing Madge executable handling
def test_missing_madge_executable(tmp_path: Path):
    """When Madge is not installed, return status 'unavailable' with MADGE_NOT_FOUND."""
    with patch("backend.app.services.dependency_impact.madge_runner.resolve_madge_command", return_value=None):
        res = run_madge(str(tmp_path))
        assert res["status"] == STATUS_UNAVAILABLE
        assert res["dependency_map"] is None
        assert res["cycles"] is None
        assert res["error"]["code"] == ERR_MADGE_NOT_FOUND
        assert not res["metadata"]["dependency_map_available"]


# Test 3: Successful dependency map parsing (mocked)
def test_successful_dependency_map(tmp_path: Path):
    """Mock valid JSON output from Madge and verify clean parsing."""
    mock_stdout = json.dumps({
        "src/main.ts": ["src/app.ts", "src/utils.ts"],
        "src/app.ts": ["src/utils.ts"],
        "src/utils.ts": [],
    })

    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(0, mock_stdout, "", False, False),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_SUCCESS
        assert res["error"] is None
        assert "src/main.ts" in res["dependency_map"]
        assert res["dependency_map"]["src/main.ts"] == ["src/app.ts", "src/utils.ts"]
        assert res["dependency_map"]["src/utils.ts"] == []


# Test 4: Genuine empty dependency map
def test_empty_dependency_map(tmp_path: Path):
    """When Madge runs cleanly and returns '{}', dependency_map must be {} and status success."""
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(0, "{}", "", False, False),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_SUCCESS
        assert res["dependency_map"] == {}
        assert res["error"] is None


# Test 5: Invalid JSON handling
def test_invalid_json_handling(tmp_path: Path):
    """When Madge returns non-JSON stdout, return status 'failed' with MADGE_INVALID_JSON."""
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(0, "Syntax error in some file", "", False, False),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_FAILED
        assert res["dependency_map"] is None
        assert res["error"]["code"] == ERR_MADGE_INVALID_JSON


# Test 6: Non-zero exit code handling
def test_nonzero_exit_code_handling(tmp_path: Path):
    """When Madge exits non-zero without valid JSON, return status 'failed' with MADGE_EXECUTION_FAILED."""
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(1, "", "Fatal error: unable to resolve entry point", False, False),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_FAILED
        assert res["dependency_map"] is None
        assert res["error"]["code"] == ERR_MADGE_EXECUTION_FAILED
        assert "unable to resolve entry point" in res["error"]["message"]


# Test 7: Subprocess timeout handling
def test_subprocess_timeout(tmp_path: Path):
    """When Madge execution exceeds timeout, return status 'failed' with MADGE_TIMEOUT."""
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(None, "", "", True, False),
    ):
        res = get_dependency_map(str(tmp_path), timeout_seconds=5, madge_bin="fake-madge")
        assert res["status"] == STATUS_FAILED
        assert res["dependency_map"] is None
        assert res["error"]["code"] == ERR_MADGE_TIMEOUT
        assert res["error"]["retryable"] is True


# Test 8: Invalid repository path handling
def test_invalid_repository_path():
    """Verify empty paths, invalid types, or non-existent directories return error."""
    res1 = run_madge("")
    assert res1["status"] == STATUS_FAILED
    assert res1["error"]["code"] == ERR_REPOSITORY_PATH_INVALID

    res2 = run_madge("C:/NonExistentPath_XYZ_123456")
    assert res2["status"] == STATUS_FAILED
    assert res2["error"]["code"] == ERR_REPOSITORY_NOT_FOUND


# Test 9: Path normalisation and traversal rejection
def test_path_normalisation():
    """Verify that Windows separators are normalized and directory traversal is rejected."""
    assert normalize_repo_relative_path("src\\services\\auth.ts") == "src/services/auth.ts"
    assert normalize_repo_relative_path("./src/app.ts") == "src/app.ts"
    assert normalize_repo_relative_path("src/components/../utils.ts") is None
    assert normalize_repo_relative_path("C:\\DeadCode\\src\\app.ts") is None
    assert normalize_repo_relative_path("/etc/passwd") is None
    assert normalize_repo_relative_path("") is None


# Test 10: Circular dependency extraction (mocked)
def test_circular_dependency_parsing(tmp_path: Path):
    """Verify cycle parsing normalises paths and preserves cycles."""
    mock_cycles = [
        ["src\\services\\auth.ts", "src\\services\\user.ts"],
        ["src/a.ts", "src/b.ts", "src/c.ts"],
    ]
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(1, json.dumps(mock_cycles), "", False, False),
    ):
        res = get_circular_dependencies(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_SUCCESS
        assert res["error"] is None
        assert len(res["cycles"]) == 2
        assert res["cycles"][0] == ["src/services/auth.ts", "src/services/user.ts"]
        assert res["cycles"][1] == ["src/a.ts", "src/b.ts", "src/c.ts"]


# Test 11: Partial extraction handling
def test_partial_extraction_handling(tmp_path: Path):
    """If dependency extraction succeeds but cycle extraction fails, status must be 'partial'."""
    mock_dep_stdout = json.dumps({"src/main.ts": ["src/app.ts"]})

    def mock_run_bounded(cmd, *args, **kwargs):
        if "--circular" in cmd:
            return (2, "", "Cycle engine memory crash", False, False)
        return (0, mock_dep_stdout, "", False, False)

    with patch("backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded", side_effect=mock_run_bounded):
        res = run_madge(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_PARTIAL
        assert res["dependency_map"] == {"src/main.ts": ["src/app.ts"]}
        assert res["cycles"] is None
        assert len(res["warnings"]) > 0
        assert res["warnings"][0]["code"] == ERR_MADGE_PARTIAL_OUTPUT
        assert res["metadata"]["dependency_map_available"] is True
        assert res["metadata"]["cycles_available"] is False


# Test 12: No absolute path leakage in error sanitisation
def test_error_sanitization():
    """Verify that absolute host paths are sanitized from public error messages."""
    raw = "Error occurred in C:\\DeadCode\\backend\\app\\secret.py at /home/user/code"
    sanitized = sanitize_message(raw, repo_path="C:\\DeadCode")
    assert "C:\\DeadCode" not in sanitized
    assert "<path>" in sanitized or "<repo_root>" in sanitized


# Test 13: Subprocess security: uses argument list and shell=False
def test_subprocess_security_parameters(tmp_path: Path):
    """Verify subprocess is invoked with an argument list and shell=False."""
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.stdout.read.return_value = b"{}"
        mock_proc.stderr.read.return_value = b""
        mock_popen.return_value = mock_proc

        get_dependency_map(str(tmp_path), madge_bin="test-madge.js")

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        assert isinstance(cmd, list), "Command must be an argument list"
        assert kwargs.get("shell") is False, "shell must strictly be False"
        assert kwargs.get("cwd") == str(tmp_path.resolve())


# Test 14: Output validation rejects non-dict dependency map
def test_malformed_root_structure_rejected(tmp_path: Path):
    """When Madge returns a JSON list instead of an object, reject it as invalid."""
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(0, '["unexpected", "list"]', "", False, False),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge")
        assert res["status"] == STATUS_FAILED
        assert res["error"]["code"] == ERR_MADGE_INVALID_JSON


# Test 15: REAL INTEGRATION TEST against the controlled TypeScript fixture
def test_real_madge_integration_on_fixture():
    """Execute real Madge against the controlled TS fixture without mocks."""
    assert FIXTURE_PATH.exists(), f"Fixture path {FIXTURE_PATH} must exist"

    result = run_madge(str(FIXTURE_PATH))

    assert result["status"] == STATUS_SUCCESS, f"Expected success but got: {result}"
    assert result["error"] is None

    dep_map = result["dependency_map"]
    assert dep_map is not None
    assert "src/main.ts" in dep_map
    assert "src/app.ts" in dep_map["src/main.ts"]

    assert "src/app.ts" in dep_map
    assert "src/utils.ts" in dep_map["src/app.ts"]

    assert "src/utils.ts" in dep_map
    assert dep_map["src/utils.ts"] == []

    cycles = result["cycles"]
    assert cycles is not None
    assert len(cycles) >= 1
    cycle_files = set()
    for cycle in cycles:
        cycle_files.update(cycle)

    assert "src/services/auth.ts" in cycle_files
    assert "src/services/user.ts" in cycle_files

    metadata = result["metadata"]
    assert metadata["madge_version"] == "8.0.0"
    assert metadata["dependency_map_available"] is True
    assert metadata["cycles_available"] is True
    assert metadata["execution_time_ms"] >= 0


# ==============================================================================
# SECTION 2: SUBPROCESS OUTPUT LIMITS & IN-FLIGHT STREAMING PROTECTION TESTS
# ==============================================================================

# Test 16: Stdout below configured limit runs normally
def test_stdout_below_limit(tmp_path: Path):
    """A subprocess writing stdout below the limit succeeds normally."""
    cmd = [sys.executable, "-c", "import sys; sys.stdout.write('hello world')"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=1000)
    assert ret == 0
    assert out == "hello world"
    assert not timed_out
    assert not overflowed


# Test 17: Stderr below configured limit runs normally
def test_stderr_below_limit(tmp_path: Path):
    """A subprocess writing stderr below the limit succeeds normally."""
    cmd = [sys.executable, "-c", "import sys; sys.stderr.write('warning message')"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=1000)
    assert ret == 0
    assert err == "warning message"
    assert not timed_out
    assert not overflowed


# Test 18: Stdout exceeding limit triggers overflow termination
def test_stdout_exceeding_limit(tmp_path: Path):
    """When a subprocess writes more bytes than allowed to stdout, it is killed."""
    # Writes 50,000 bytes when limit is 5,000
    cmd = [sys.executable, "-c", "import sys; sys.stdout.write('A' * 50000); sys.stdout.flush()"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=5000)
    assert overflowed is True
    assert len(out.encode("utf-8")) <= 5000


# Test 19: Stderr exceeding limit triggers overflow termination
def test_stderr_exceeding_limit(tmp_path: Path):
    """When a subprocess writes more bytes than allowed to stderr, it is killed."""
    cmd = [sys.executable, "-c", "import sys; sys.stderr.write('E' * 50000); sys.stderr.flush()"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=5000)
    assert overflowed is True
    assert len(err.encode("utf-8")) <= 5000


# Test 20: Both streams producing large output concurrently do not deadlock
def test_concurrent_large_streams_no_deadlock(tmp_path: Path):
    """Concurrently writing to stdout and stderr must not deadlock pipe buffers."""
    code = (
        "import sys\n"
        "for i in range(100):\n"
        "    sys.stdout.write('X' * 500 + '\\n')\n"
        "    sys.stderr.write('Y' * 500 + '\\n')\n"
        "    sys.stdout.flush()\n"
        "    sys.stderr.flush()\n"
    )
    cmd = [sys.executable, "-c", code]
    # Set limit high enough for 100 iterations (approx 100KB)
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=200000)
    assert ret == 0
    assert not overflowed
    assert not timed_out
    assert len(out) > 10000
    assert len(err) > 10000


# Test 21: Valid JSON output below limit parses properly in runner
def test_valid_json_below_limit_parsed(tmp_path: Path):
    """Valid JSON from a real process below the output limit is parsed cleanly."""
    valid_json = '{"src/a.ts": ["src/b.ts"], "src/b.ts": []}'
    cmd = [sys.executable, "-c", f"import sys; sys.stdout.write({json.dumps(valid_json)})"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=10000)
    assert ret == 0
    data = json.loads(out)
    assert data["src/a.ts"] == ["src/b.ts"]


# Test 22: JSON truncated because of output overflow returns MADGE_OUTPUT_LIMIT_EXCEEDED
def test_truncated_json_overflow_is_failure(tmp_path: Path):
    """If output overflows, the runner returns MADGE_OUTPUT_LIMIT_EXCEEDED, not empty success."""
    # Overflow mock
    with patch(
        "backend.app.services.dependency_impact.madge_runner.run_subprocess_bounded",
        return_value=(None, '{"truncated', "", False, True),
    ):
        res = get_dependency_map(str(tmp_path), madge_bin="fake-madge", max_output_bytes=100)
        assert res["status"] == STATUS_FAILED
        assert res["dependency_map"] is None
        assert res["error"]["code"] == ERR_MADGE_OUTPUT_LIMIT_EXCEEDED


# Test 23: Timeout during output streaming terminates process
def test_timeout_during_output_streaming(tmp_path: Path):
    """A subprocess sleeping past the timeout is terminated and flagged timed_out."""
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), timeout_seconds=0.2)
    assert timed_out is True
    assert not overflowed


# Test 24: Process cleanup after output overflow leaves no orphan
def test_cleanup_after_output_overflow(tmp_path: Path):
    """Process is guaranteed terminated following an output overflow."""
    cmd = [sys.executable, "-c", "import sys, time; sys.stdout.write('X' * 50000); sys.stdout.flush(); time.sleep(2)"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), max_output_bytes=5000)
    assert overflowed is True
    # The process has exited/been killed (ret is not None)
    assert ret is not None


# Test 25: Process cleanup after timeout leaves no orphan
def test_cleanup_after_timeout(tmp_path: Path):
    """Process is guaranteed terminated following a timeout."""
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    ret, out, err, timed_out, overflowed = run_subprocess_bounded(cmd, cwd=str(tmp_path), timeout_seconds=0.2)
    assert timed_out is True
    assert ret is not None


# ==============================================================================
# SECTION 3: WINDOWS EXECUTION & DIRECT NODE.JS INVOCATION TESTS
# ==============================================================================

# Test 26: Node.js executable discovery
def test_node_executable_discovery():
    """Verify Node.js is located on PATH."""
    node_bin = find_node_executable()
    assert node_bin is not None
    assert "node" in node_bin.lower()


# Test 27: Local Madge CLI entrypoint discovery
def test_local_madge_entrypoint_discovery():
    """Verify Madge JavaScript entry point cli.js is discovered under tooling/."""
    entry = find_madge_entrypoint()
    assert entry is not None
    assert entry.endswith("cli.js")
    assert Path(entry).exists()


# Test 28: Direct Node.js command resolution
def test_resolve_madge_command_uses_node():
    """Verify resolve_madge_command creates an argument list starting with node and cli.js."""
    cmd = resolve_madge_command()
    assert cmd is not None
    assert len(cmd) == 2
    assert "node" in cmd[0].lower()
    assert cmd[1].endswith("cli.js")


# Test 29: Invocation with shell=False explicitly validated
def test_invocation_shell_false_contract(tmp_path: Path):
    """Confirm Popen is called with shell=False when invoking Madge."""
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.stdout.read.return_value = b"{}"
        mock_proc.stderr.read.return_value = b""
        mock_popen.return_value = mock_proc

        run_subprocess_bounded(["node", "cli.js"], cwd=str(tmp_path))

        mock_popen.assert_called_once()
        _, kwargs = mock_popen.call_args
        assert kwargs.get("shell") is False


# Test 30: Repository path containing spaces works seamlessly
def test_repository_path_with_spaces(tmp_path: Path):
    """A repository path with spaces executes cleanly without shell quoting failure."""
    spaced_dir = tmp_path / "repo with spaces"
    spaced_dir.mkdir()
    # Copy fixture files into spaced dir
    src_dir = spaced_dir / "src"
    src_dir.mkdir()
    (src_dir / "a.ts").write_text("import './b';\n", encoding="utf-8")
    (src_dir / "b.ts").write_text("export const b = 1;\n", encoding="utf-8")

    res = run_madge(str(spaced_dir))
    assert res["status"] == STATUS_SUCCESS
    assert "src/a.ts" in res["dependency_map"]
    assert res["dependency_map"]["src/a.ts"] == ["src/b.ts"]


# Test 31: Working directory is strictly the target repository
def test_working_directory_handling(tmp_path: Path):
    """Verify that cwd passed to subprocess is the resolved repository path."""
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.stdout.read.return_value = b"{}"
        mock_proc.stderr.read.return_value = b""
        mock_popen.return_value = mock_proc

        get_dependency_map(str(tmp_path))

        mock_popen.assert_called_once()
        _, kwargs = mock_popen.call_args
        assert kwargs.get("cwd") == str(tmp_path.resolve())


# Test 32: Real Madge dependency map on fixture
def test_real_madge_fixture_dependency_map():
    """Verify dependency map extraction from real Madge on the TS fixture."""
    res = get_dependency_map(str(FIXTURE_PATH))
    assert res["status"] == STATUS_SUCCESS
    assert "src/app.ts" in res["dependency_map"]
    assert res["dependency_map"]["src/app.ts"] == ["src/utils.ts"]


# Test 33: Real Madge circular dependencies on fixture
def test_real_madge_fixture_circular_dependencies():
    """Verify circular dependency extraction from real Madge on the TS fixture."""
    res = get_circular_dependencies(str(FIXTURE_PATH))
    assert res["status"] == STATUS_SUCCESS
    assert len(res["cycles"]) == 1
    cycle = res["cycles"][0]
    assert "src/services/auth.ts" in cycle
    assert "src/services/user.ts" in cycle


# Test 34: Missing Node.js executable returns UNAVAILABLE
def test_missing_node_executable(tmp_path: Path):
    """If Node.js is missing when resolving a JS script, return UNAVAILABLE."""
    with patch("backend.app.services.dependency_impact.madge_runner.find_node_executable", return_value=None):
        with patch("backend.app.services.dependency_impact.madge_runner.find_madge_executable", return_value="madge.js"):
            res = get_dependency_map(str(tmp_path))
            assert res["status"] == STATUS_UNAVAILABLE
            assert res["error"]["code"] == ERR_MADGE_NOT_FOUND


# Test 35: Missing Madge installation returns UNAVAILABLE
def test_missing_madge_installation(tmp_path: Path):
    """If Madge cannot be found anywhere, return UNAVAILABLE."""
    with patch("backend.app.services.dependency_impact.madge_runner.find_madge_executable", return_value=None):
        res = get_dependency_map(str(tmp_path))
        assert res["status"] == STATUS_UNAVAILABLE
        assert res["error"]["code"] == ERR_MADGE_NOT_FOUND
