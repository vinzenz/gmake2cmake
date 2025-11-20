from __future__ import annotations

import io
from pathlib import Path

import pytest

from gmake2cmake import cli
from gmake2cmake.diagnostics import add, DiagnosticCollector
from tests.conftest import FakeFS


def test_parse_args_defaults_and_packaging():
    args = cli.parse_args([])
    assert args.source_dir.is_absolute()
    assert args.output_dir.is_absolute()
    assert args.entry_makefile is None
    assert args.with_packaging is False

    args = cli.parse_args(["--with-packaging", "-f", "Makefile"])
    assert args.with_packaging is True
    assert args.entry_makefile == "Makefile"


def test_run_propagates_errors_and_report(tmp_path, monkeypatch):
    fs = FakeFS()
    reports = []

    def fake_stdout():
        return io.StringIO()

    monkeypatch.setattr(cli, "_stdout", fake_stdout)

    def fake_pipeline(ctx: cli.RunContext):
        add(ctx.diagnostics, "ERROR", "TEST", "boom")

    exit_code = cli.run(["--source-dir", str(tmp_path)], fs=fs, pipeline_fn=fake_pipeline)
    assert exit_code == 1

    # ensure report writing works when requested and dry-run preserves tests
    exit_code = cli.run(
        ["--source-dir", str(tmp_path), "--report", "--with-packaging"],
        fs=fs,
        pipeline_fn=lambda ctx: None,
    )
    assert exit_code == 0
    assert any(path.name == "report.json" for path in fs.store)


def test_run_handles_invalid_args(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(cli, "_stdout", lambda: buf)
    code = cli.run(["--output-dir", ""], fs=FakeFS())
    assert code == 1
    assert "Unhandled exception" in buf.getvalue()
