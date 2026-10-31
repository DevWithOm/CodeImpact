"""Safe subprocess execution utility for static analysis tools.

Guarantees shell=False, parameter validation, timeout handling, and structured results.
"""

from dataclasses import dataclass
import os
import subprocess
import time


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def run_command(
    args: list[str],
    cwd: str | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Executes an external command safely using subprocess.run with shell=False.

    Args:
        args: Command arguments list, where args[0] is the executable.
        cwd: Directory in which to execute the command.
        timeout: Maximum seconds to wait before terminating process.
        env: Optional environment variables dictionary.

    Returns:
        CommandResult with returncode, stdout, stderr, and timeout status.
    """
    if not args or not isinstance(args, list):
        raise ValueError("Command arguments must be a non-empty list of strings.")

    # Ensure all arguments are strings
    sanitized_args = [str(arg) for arg in args]

    # Merge environment if provided
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    start_time = time.monotonic()
    try:
        proc = subprocess.run(
            sanitized_args,
            cwd=cwd,
            timeout=timeout,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=run_env,
        )
        duration = time.monotonic() - start_time
        return CommandResult(
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            timed_out=False,
            duration_seconds=round(duration, 3),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start_time
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8", "replace") if exc.stdout else "")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8", "replace") if exc.stderr else "")
        return CommandResult(
            exit_code=-1,
            stdout=stdout,
            stderr=f"Process timed out after {timeout} seconds. {stderr}".strip(),
            timed_out=True,
            duration_seconds=round(duration, 3),
        )
    except Exception as exc:
        duration = time.monotonic() - start_time
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr=f"Failed to execute command: {str(exc)}",
            timed_out=False,
            duration_seconds=round(duration, 3),
        )
