"""Tests for logging configuration module."""

from __future__ import annotations

import io
import logging

from gmake2cmake.logging_config import get_logger, setup_logging


def test_setup_logging_defaults():
    """Test logging setup with default parameters."""
    stream = io.StringIO()
    setup_logging(verbosity=0, stream=stream)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.ERROR


def test_setup_logging_verbosity_levels():
    """Test logging verbosity levels are set correctly."""
    for verbosity, expected_level in [(0, logging.ERROR), (1, logging.WARNING), (2, logging.INFO), (3, logging.DEBUG)]:
        stream = io.StringIO()
        setup_logging(verbosity=verbosity, stream=stream)
        root_logger = logging.getLogger()
        assert root_logger.level == expected_level


def test_setup_logging_output_to_stream():
    """Test logging output to custom stream."""
    stream = io.StringIO()
    setup_logging(verbosity=2, stream=stream)

    test_logger = logging.getLogger("test.module")
    test_logger.info("test message")

    output = stream.getvalue()
    assert "test message" in output
    assert "INFO" in output


def test_setup_logging_file_output(tmp_path):
    """Test logging output to file."""
    log_file = tmp_path / "test.log"
    stream = io.StringIO()
    setup_logging(verbosity=2, log_file=log_file, stream=stream)

    test_logger = logging.getLogger("test.module")
    test_logger.info("file test message")

    assert log_file.exists()
    content = log_file.read_text()
    assert "file test message" in content


def test_setup_logging_verbose_format():
    """Test logging format changes with verbosity."""
    stream = io.StringIO()
    setup_logging(verbosity=3, stream=stream)

    test_logger = logging.getLogger("test.verbose")
    test_logger.debug("debug message")

    output = stream.getvalue()
    assert "debug message" in output
    # Verbose format includes filename and line number
    assert "test_logging.py" in output


def test_get_logger():
    """Test getting logger instances."""
    logger1 = get_logger("module.a")
    logger2 = get_logger("module.a")
    logger3 = get_logger("module.b")

    assert logger1 is logger2
    assert logger1 is not logger3
    assert logger1.name == "module.a"
    assert logger3.name == "module.b"


def test_logging_does_not_clash_with_diagnostics():
    """Test that logging setup does not interfere with diagnostics."""
    from gmake2cmake.diagnostics import DiagnosticCollector, add

    stream = io.StringIO()
    setup_logging(verbosity=2, stream=stream)

    diagnostics = DiagnosticCollector()
    add(diagnostics, "ERROR", "CONFIG_MISSING", "test message")

    # Verify diagnostics still work independently
    assert len(diagnostics.diagnostics) == 1
    assert diagnostics.diagnostics[0].code == "CONFIG_MISSING"


def test_setup_logging_is_idempotent():
    """Test that calling setup_logging multiple times works correctly."""
    stream1 = io.StringIO()
    setup_logging(verbosity=1, stream=stream1)

    stream2 = io.StringIO()
    setup_logging(verbosity=2, stream=stream2)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1  # Should have only one console handler


def test_logging_file_creation_with_parents(tmp_path):
    """Test that log file parent directories are created."""
    log_file = tmp_path / "logs" / "subdir" / "test.log"
    stream = io.StringIO()
    setup_logging(verbosity=2, log_file=log_file, stream=stream)

    test_logger = logging.getLogger("test")
    test_logger.info("test")

    assert log_file.exists()
    assert log_file.parent.exists()
