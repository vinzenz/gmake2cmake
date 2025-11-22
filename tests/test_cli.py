from __future__ import annotations

import io
import json
import sys

import pytest

from gmake2cmake import cli
from gmake2cmake.diagnostics import add
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
    report_path = next(path for path in fs.store if path.name == "report.json")
    payload = json.loads(fs.store[report_path])
    assert "diagnostics" in payload and "unknown_constructs" in payload and "introspection" in payload
    assert payload["introspection"]["introspection_enabled"] is False
    assert payload["introspection"]["validated_count"] == 0
    report_md = next(path for path in fs.store if path.name == "report.md")
    assert "Unknown Constructs" in fs.store[report_md]


def test_run_handles_invalid_args(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(cli, "_stdout", lambda: buf)
    code = cli.run(["--output-dir", ""], fs=FakeFS())
    assert code == 1
    assert "Unhandled exception" in buf.getvalue()


def test_introspection_flag_requires_make(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(cli, "_stdout", lambda: buf)
    monkeypatch.setattr(cli, "_make_in_path", lambda: False)
    code = cli.run(["--source-dir", ".", "--use-make-introspection"], fs=FakeFS())
    assert code == 1
    assert "GNU make not found" in buf.getvalue()


def test_main_exits_with_run_code(monkeypatch):
    called = {}

    def fake_run(argv, **kwargs):
        called["argv"] = argv
        return 3

    monkeypatch.setattr(cli, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["gmake2cmake", "--source-dir", "proj"])
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 3
    assert called["argv"] == ["--source-dir", "proj"]


# Exit code category tests
def test_exit_code_success():
    """Test that no errors returns success code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, exit_code
    collector = DiagnosticCollector()
    assert exit_code(collector) == 0


def test_exit_code_usage_error():
    """Test that CLI_UNHANDLED error returns USAGE code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "CLI_UNHANDLED", "Invalid arguments")
    assert exit_code(collector) == 1


def test_exit_code_config_error():
    """Test that config errors return CONFIG code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "CONFIG_MISSING", "Config file not found")
    assert exit_code(collector) == 2


def test_exit_code_parse_error():
    """Test that parse errors return PARSE code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "EVAL_RECURSIVE_LOOP", "Recursive variable loop")
    assert exit_code(collector) == 3


def test_exit_code_build_error():
    """Test that build/IR errors return BUILD code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "IR_DUP_TARGET", "Duplicate target")
    assert exit_code(collector) == 4


def test_exit_code_io_error():
    """Test that IO/emit errors return IO code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "EMIT_WRITE_FAIL", "Failed to write output")
    assert exit_code(collector) == 5


def test_exit_code_mixed_errors_prioritizes_config():
    """Test that mixed errors prioritize config errors."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "CONFIG_MISSING", "Config missing")
    add(collector, "ERROR", "EMIT_WRITE_FAIL", "IO error")
    # CONFIG (2) > IO (5), so should return 2
    assert exit_code(collector) == 2


def test_exit_code_mixed_errors_prioritizes_io():
    """Test that IO errors are prioritized over build errors."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "ERROR", "EMIT_WRITE_FAIL", "IO error")
    add(collector, "ERROR", "IR_DUP_TARGET", "Build error")
    # IO (5) > BUILD (4), so should return 5
    assert exit_code(collector) == 5


def test_exit_code_ignores_warnings():
    """Test that warnings alone don't produce error exit code."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code
    collector = DiagnosticCollector()
    add(collector, "WARN", "CONFIG_UNKNOWN_KEY", "Unknown key")
    assert exit_code(collector) == 0


# Config validation tests
def test_validate_config_flag_valid(tmp_path, monkeypatch):
    """Test --validate-config with valid config."""
    fs = FakeFS()

    def fake_stdout():
        return io.StringIO()

    monkeypatch.setattr(cli, "_stdout", fake_stdout)

    # Create a valid config file
    config_content = "project_name: test_project\n"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    fs.write_text(config_path, config_content)

    exit_code = cli.run(
        ["--source-dir", str(tmp_path), "--config", str(config_path), "--validate-config"],
        fs=fs,
    )
    assert exit_code == 0


def test_validate_config_flag_missing_file(tmp_path, monkeypatch):
    """Test --validate-config with missing config file."""
    fs = FakeFS()

    def fake_stdout():
        return io.StringIO()

    monkeypatch.setattr(cli, "_stdout", fake_stdout)

    exit_code = cli.run(
        ["--source-dir", str(tmp_path), "--config", "/nonexistent/config.yaml", "--validate-config"],
        fs=fs,
    )
    assert exit_code == 2  # CONFIG error code


def test_validate_config_flag_invalid_schema(tmp_path, monkeypatch):
    """Test --validate-config with invalid config schema."""
    fs = FakeFS()

    def fake_stdout():
        return io.StringIO()

    monkeypatch.setattr(cli, "_stdout", fake_stdout)

    # Create an invalid config file (project_name should be string, not number)
    config_content = "project_name: 123\n"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    fs.write_text(config_path, config_content)

    exit_code = cli.run(
        ["--source-dir", str(tmp_path), "--config", str(config_path), "--validate-config"],
        fs=fs,
    )
    assert exit_code == 2  # CONFIG error code


def test_parse_args_validate_config():
    """Test that --validate-config flag is parsed correctly."""
    args = cli.parse_args(["--validate-config"])
    assert args.validate_config is True

    args = cli.parse_args([])
    assert args.validate_config is False
