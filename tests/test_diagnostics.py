from __future__ import annotations

import io

import pytest

from gmake2cmake.diagnostics import (
    Diagnostic,
    DiagnosticCollector,
    add,
    exit_code,
    extend,
    has_errors,
    to_console,
    to_json,
)


def test_dedupe_and_ordering_console():
    collector = DiagnosticCollector()
    add(collector, "WARN", "TEST", "first", "path:1")
    add(collector, "WARN", "TEST", "first", "path:1")  # duplicate
    add(collector, "ERROR", "TEST", "fatal", None)
    add(collector, "INFO", "TEST", "info", None)

    buf = io.StringIO()
    to_console(collector, stream=buf, verbose=False)
    lines = buf.getvalue().strip().splitlines()
    assert lines[0].startswith("[ERROR] TEST")
    assert len(lines) == 3


def test_has_errors_and_exit():
    collector = DiagnosticCollector()
    add(collector, "WARN", "TEST", "warn")
    assert has_errors(collector) is False
    assert exit_code(collector) == 0
    add(collector, "ERROR", "TEST", "err")
    assert has_errors(collector) is True
    assert exit_code(collector) == 1


def test_to_json_stable_order():
    collector = DiagnosticCollector()
    extend(
        collector,
        [
            Diagnostic(severity="INFO", code="TEST", message="one", location=None, origin=None),
            Diagnostic(severity="WARN", code="TEST", message="two", location="f:1", origin="o"),
        ],
    )
    output = to_json(collector)
    assert '"severity": "INFO"' in output
    assert '"code": "TEST"' in output


def test_diagnostic_validation():
    # Valid diagnostic with registered code
    d = Diagnostic(severity="ERROR", code="TEST", message="Test message")
    assert d.severity == "ERROR"

    # Invalid: bad severity
    with pytest.raises(ValueError, match="Invalid severity"):
        Diagnostic(severity="BADLEVEL", code="TEST", message="msg")

    # Invalid: empty code
    with pytest.raises(ValueError, match="code cannot be empty"):
        Diagnostic(severity="WARN", code="", message="msg")

    # Invalid: empty message
    with pytest.raises(ValueError, match="message cannot be empty"):
        Diagnostic(severity="INFO", code="TEST", message="")

    # Invalid: unregistered code
    with pytest.raises(ValueError, match="Invalid diagnostic code"):
        Diagnostic(severity="WARN", code="NONEXISTENT_CODE", message="msg")

    # Valid: with location and origin
    d = Diagnostic(
        severity="WARN",
        code="CONFIG_UNKNOWN_KEY",
        message="A warning",
        location="file.mk:10",
        origin="parser",
    )
    assert d.location == "file.mk:10"
    assert d.origin == "parser"
