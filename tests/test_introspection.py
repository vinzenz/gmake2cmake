from __future__ import annotations

from pathlib import Path

from gmake2cmake import introspection
from gmake2cmake.diagnostics import DiagnosticCollector


class DummyProcessResult:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_introspection_runs_make_with_flags(monkeypatch):
    captured = {}

    def runner(cmd, capture_output, text, env, timeout):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["timeout"] = timeout
        return DummyProcessResult(stdout="db", stderr="", returncode=0)

    diagnostics = DiagnosticCollector()
    result = introspection.run(Path("/proj"), diagnostics, process_runner=runner, timeout=5.0)

    assert captured["cmd"] == ["make", "-pn", "-C", "/proj"]
    assert captured["env"]["MAKEFLAGS"] == "-Rr"
    assert captured["env"]["MAKELEVEL"] == "0"
    assert captured["timeout"] == 5.0
    assert result.stdout == "db"
    assert not diagnostics.diagnostics


def test_introspection_timeout_records_diag():
    def runner(cmd, capture_output, text, env, timeout):
        raise introspection.subprocess.TimeoutExpired(cmd, timeout=timeout)

    diagnostics = DiagnosticCollector()
    result = introspection.run(Path("/proj"), diagnostics, process_runner=runner, timeout=0.1)

    assert result.returncode == 124
    assert any(d.code == "INTROSPECTION_TIMEOUT" for d in diagnostics.diagnostics)


def test_introspection_failure_status_warns():
    diagnostics = DiagnosticCollector()
    result = introspection.run(
        Path("/proj"),
        diagnostics,
        process_runner=lambda *args, **kwargs: DummyProcessResult(stdout="", stderr="boom", returncode=2),
    )
    assert result.returncode == 2
    assert any(d.code == "INTROSPECTION_FAILED" for d in diagnostics.diagnostics)


def test_introspection_truncates_large_output():
    diagnostics = DiagnosticCollector()
    payload = "x" * (3_000_000)

    result = introspection.run(
        Path("/proj"),
        diagnostics,
        process_runner=lambda *args, **kwargs: DummyProcessResult(stdout=payload, stderr="", returncode=0),
        max_output_bytes=1024,
    )

    assert len(result.stdout.encode("utf-8")) == 1024
    assert result.truncated is True
    assert any(d.code == "INTROSPECTION_FAILED" for d in diagnostics.diagnostics)
