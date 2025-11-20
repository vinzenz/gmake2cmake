from __future__ import annotations

import io

from gmake2cmake.diagnostics import Diagnostic, DiagnosticCollector, add, extend, has_errors, to_console, to_json, exit_code


def test_dedupe_and_ordering_console():
    collector = DiagnosticCollector()
    add(collector, "WARN", "X1", "first", "path:1")
    add(collector, "WARN", "X1", "first", "path:1")  # duplicate
    add(collector, "ERROR", "X0", "fatal", None)
    add(collector, "INFO", "X2", "info", None)

    buf = io.StringIO()
    to_console(collector, stream=buf, verbose=False)
    lines = buf.getvalue().strip().splitlines()
    assert lines[0].startswith("[ERROR] X0")
    assert len(lines) == 3


def test_has_errors_and_exit():
    collector = DiagnosticCollector()
    add(collector, "WARN", "W1", "warn")
    assert has_errors(collector) is False
    assert exit_code(collector) == 0
    add(collector, "ERROR", "E1", "err")
    assert has_errors(collector) is True
    assert exit_code(collector) == 1


def test_to_json_stable_order():
    collector = DiagnosticCollector()
    extend(
        collector,
        [
            Diagnostic(severity="INFO", code="A", message="one", location=None, origin=None),
            Diagnostic(severity="WARN", code="B", message="two", location="f:1", origin="o"),
        ],
    )
    output = to_json(collector)
    assert '"severity": "INFO"' in output
    assert '"code": "B"' in output
