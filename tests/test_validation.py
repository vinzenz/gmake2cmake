from __future__ import annotations

from pathlib import Path

from gmake2cmake import cli, config
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.validation import MAX_CONFIG_BYTES, validate_cli_args, validate_identifier_field
from tests.conftest import FakeFS


def test_validate_cli_args_blocks_traversal_in_entry_makefile():
    diagnostics = DiagnosticCollector()
    args = cli.CLIArgs(
        source_dir=Path("/proj"),
        entry_makefile="../Makefile",
        output_dir=Path("/out"),
        config_path=None,
        dry_run=False,
        report=False,
        verbose=0,
        strict=False,
        processes=None,
        with_packaging=False,
        log_file=None,
        log_max_bytes=0,
        log_backup_count=3,
        log_rotate_when=None,
        log_rotate_interval=1,
        syslog_address=None,
        profile=False,
        validate_config=False,
    )
    validate_cli_args(args, diagnostics)
    codes = {d.code for d in diagnostics.diagnostics}
    assert "VALIDATION_PATH" in codes


def test_validate_identifier_field_rejects_invalid_chars():
    diagnostics = DiagnosticCollector()
    result = validate_identifier_field("bad name!", "project_name", diagnostics)
    assert result is None
    assert any(d.code == "VALIDATION_IDENTIFIER" for d in diagnostics.diagnostics)


def test_config_rejects_oversized_file():
    diagnostics = DiagnosticCollector()
    fs = FakeFS()
    path = Path("/cfg.yaml")
    fs.store[path] = "a" * (MAX_CONFIG_BYTES + 10)

    data = config.load_yaml(path, fs=fs, diagnostics=diagnostics)
    assert data == {}
    assert any(d.code == "CONFIG_TOO_LARGE" for d in diagnostics.diagnostics)
