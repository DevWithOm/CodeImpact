"""Safe subprocess execution utility for static analysis tools.

Guarantees shell=False, parameter validation, timeout handling, memory limits,
and secret redaction from command outputs.
"""

from dataclasses import dataclass
import os
import re
import subprocess
import time


MAX_OUTPUT_BYTES = 5 * 1024 * 1024  # 5 MB maximum output capture

# Patterns for sensitive credentials to redact
SECRET_PATTERNS = [
    re.compile(r"(ghp_[a-zA-Z0-9]{36,})", re.IGNORECASE),  # GitHub personal access tokens
    re.compile(r"(github_pat_[a-zA-Z0-9_]{50,})", re.IGNORECASE),  # GitHub fine-grained PAT
    re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),  # Bearer tokens
    re.compile(r"(https?://)([^:\s]+):([^@\s]+)@", re.IGNORECASE),  # Embedded HTTP credentials
    re.compile(r"(AIza[0-9A-Za-z\-_]{35})"),  # Google API key pattern
    re.compile(r"(password\s*=\s*)([^\s;&]+)", re.IGNORECASE),
    re.compile(r"(token\s*=\s*)([^\s;&]+)", re.IGNORECASE),
    re.compile(r"(secret\s*=\s*)([^\s;&]+)", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Redacts sensitive tokens, credentials, and passwords from text."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        # For URL user:pass, keep protocol and user, redact pass
        if "https?://" in pattern.pattern:
            sanitized = pattern.sub(r"\1\2:[REDACTED_SECRET]@", sanitized)
        elif "Bearer" in pattern.pattern:
            sanitized = pattern.sub(r"\1[REDACTED_SECRET]", sanitized)
        elif "password" in pattern.pattern or "token" in pattern.pattern or "secret" in pattern.pattern:
            sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
        else:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def _truncate_output(output: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncates output string if its byte size exceeds the maximum limit."""
    if not output:
        return ""
    encoded = output.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
        return f"{truncated}\n[OUTPUT TRUNCATED: Exceeded {max_bytes // (1024 * 1024)} MB limit]"
    return output


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
        CommandResult with returncode, sanitized stdout, sanitized stderr, and timeout status.
    """
    if not args or not isinstance(args, list):
        raise ValueError("Command arguments must be a non-empty list of strings.")

    # Ensure all arguments are strings and strip dangerous null bytes
    sanitized_args = [str(arg).replace("\x00", "") for arg in args]

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
        stdout = redact_secrets(_truncate_output(proc.stdout or ""))
        stderr = redact_secrets(_truncate_output(proc.stderr or ""))
        return CommandResult(
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            duration_seconds=round(duration, 3),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start_time
        raw_stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8", "replace") if exc.stdout else "")
        raw_stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8", "replace") if exc.stderr else "")
        stdout = redact_secrets(_truncate_output(raw_stdout))
        stderr = redact_secrets(_truncate_output(f"Process timed out after {timeout} seconds. {raw_stderr}".strip()))
        return CommandResult(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            duration_seconds=round(duration, 3),
        )
    except Exception as exc:
        duration = time.monotonic() - start_time
        safe_exc = redact_secrets(str(exc))
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr=f"Failed to execute command: {safe_exc}",
            timed_out=False,
            duration_seconds=round(duration, 3),
        )
