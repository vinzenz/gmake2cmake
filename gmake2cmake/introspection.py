from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from gmake2cmake.diagnostics import DiagnosticCollector, add

ProcessRunner = Callable[..., subprocess.CompletedProcess]


@dataclass
class IntrospectionResult:
    stdout: str
    stderr: str
    returncode: int
    truncated: bool = False


def run(
    source_dir: Path,
    diagnostics: DiagnosticCollector,
    *,
    process_runner: Optional[ProcessRunner] = None,
    timeout: float = 15.0,
    max_output_bytes: int = 2_000_000,
) -> IntrospectionResult:
    """Run GNU make in introspection mode (no recipe execution)."""
    runner = process_runner or subprocess.run
    cmd = ["make", "-pn", "-C", str(source_dir)]
    env = os.environ.copy()
    env.update(
        {
            "MAKEFLAGS": "-Rr",
            "MAKELEVEL": "0",
            "LC_ALL": "C",
        }
    )
    try:
        result = runner(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        add(
            diagnostics,
            "WARN",
            "INTROSPECTION_TIMEOUT",
            f"make -pn timed out after {timeout}s in {source_dir}",
        )
        return IntrospectionResult(stdout="", stderr="", returncode=124, truncated=False)
    except OSError as exc:
        add(
            diagnostics,
            "WARN",
            "INTROSPECTION_FAILED",
            f"Failed to launch make: {exc}",
        )
        return IntrospectionResult(stdout="", stderr=str(exc), returncode=1, truncated=False)

    stdout = result.stdout or ""
    truncated = False
    if len(stdout.encode("utf-8")) > max_output_bytes:
        stdout = stdout.encode("utf-8")[:max_output_bytes].decode("utf-8", errors="ignore")
        truncated = True
        add(
            diagnostics,
            "WARN",
            "INTROSPECTION_FAILED",
            f"Introspection output truncated at {max_output_bytes} bytes",
        )
    if result.returncode != 0:
        add(
            diagnostics,
            "WARN",
            "INTROSPECTION_FAILED",
            f"make -pn exited with {result.returncode}",
        )
    return IntrospectionResult(stdout=stdout, stderr=result.stderr or "", returncode=result.returncode, truncated=truncated)
