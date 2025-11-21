"""Tests for structured logging configuration module."""

from __future__ import annotations

import io
import json
import logging
import time

from gmake2cmake.logging_config import (
    get_correlation_id,
    get_logger,
    log_timed_block,
    reset_correlation_id,
    set_correlation_id,
    setup_logging,
)


def _parse_stream(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_setup_logging_defaults_and_json_format():
    """Ensure default setup configures ERROR level and JSON output."""
    stream = io.StringIO()
    reset_correlation_id()
    setup_logging(verbosity=0, stream=stream)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.ERROR

    logger = get_logger("test.module")
    logger.error("test message")
    entries = _parse_stream(stream)
    assert entries[0]["message"] == "test message"
    assert entries[0]["level"] == "ERROR"
    assert entries[0]["logger"] == "test.module"
    assert "correlation_id" in entries[0]
    assert entries[0]["file"] == "test_logging.py"
    assert entries[0]["function"]
    assert entries[0]["line"] > 0


def test_environment_log_level_overrides(monkeypatch):
    """Environment variable should override verbosity-derived level."""
    stream = io.StringIO()
    reset_correlation_id()
    monkeypatch.setenv("GMAKE2CMAKE_LOG_LEVEL", "DEBUG")

    setup_logging(verbosity=0, stream=stream)
    assert logging.getLogger().level == logging.DEBUG


def test_correlation_id_propagates_across_logs():
    """Correlation ID should be stable across records."""
    stream = io.StringIO()
    reset_correlation_id()
    set_correlation_id("trace-123")
    setup_logging(verbosity=2, stream=stream)
    logger = get_logger("test.module")

    logger.warning("first")
    logger.info("second")

    entries = _parse_stream(stream)
    assert {entry["correlation_id"] for entry in entries} == {"trace-123"}


def test_log_rotation_by_size(tmp_path):
    """Structured file handler should rotate by size."""
    stream = io.StringIO()
    reset_correlation_id()
    log_file = tmp_path / "logs" / "app.log"
    setup_logging(
        verbosity=2,
        log_file=log_file,
        stream=stream,
        max_bytes=200,
        backup_count=2,
    )
    logger = get_logger("rotate.test")
    for _ in range(20):
        logger.info("x" * 50)

    rotated = log_file.with_name(log_file.name + ".1")
    assert log_file.exists()
    assert rotated.exists()


def test_log_timed_block_emits_duration():
    """Timing helper should report durations with structured payload."""
    stream = io.StringIO()
    reset_correlation_id()
    setup_logging(verbosity=2, stream=stream)

    with log_timed_block("integration", verbosity=2, logger_name="test.timer"):
        time.sleep(0.001)

    entries = _parse_stream(stream)
    events = {entry["event"] for entry in entries}
    assert {"start", "complete"} <= events
    complete_entry = next(entry for entry in entries if entry["event"] == "complete")
    assert complete_entry["operation"] == "integration"
    assert complete_entry["duration_ms"] > 0


def test_syslog_handler_attached(monkeypatch):
    """Syslog handler can be configured without raising."""
    attached = {}

    class DummySysLogHandler(logging.Handler):  # pragma: no cover - minimal shim
        def __init__(self, address):
            super().__init__()
            attached["address"] = address

        def emit(self, record):
            attached["last_message"] = record.getMessage()

    monkeypatch.setattr("gmake2cmake.logging_config.SysLogHandler", DummySysLogHandler)

    stream = io.StringIO()
    reset_correlation_id()
    setup_logging(verbosity=2, stream=stream, syslog_address="/dev/log")
    get_logger("syslog.test").info("syslog wiring")

    root_logger = logging.getLogger()
    assert any(isinstance(h, DummySysLogHandler) for h in root_logger.handlers)
    assert attached["address"] == "/dev/log"


def test_setup_logging_is_idempotent():
    """Repeated setup should replace existing handlers."""
    stream1 = io.StringIO()
    reset_correlation_id()
    setup_logging(verbosity=1, stream=stream1)

    stream2 = io.StringIO()
    setup_logging(verbosity=2, stream=stream2)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1


def test_log_file_parents_created(tmp_path):
    """Log file handler should create parent directories."""
    log_file = tmp_path / "logs" / "subdir" / "test.log"
    stream = io.StringIO()
    reset_correlation_id()
    setup_logging(verbosity=2, log_file=log_file, stream=stream)

    get_logger("test").info("test")

    assert log_file.exists()
    assert log_file.parent.exists()


def test_env_correlation_id(monkeypatch):
    """Correlation ID should honor environment override."""
    stream = io.StringIO()
    reset_correlation_id()
    monkeypatch.setenv("GMAKE2CMAKE_CORRELATION_ID", "env-trace")

    setup_logging(verbosity=2, stream=stream)
    get_logger("test").info("message")

    assert get_correlation_id() == "env-trace"
    entry = _parse_stream(stream)[0]
    assert entry["correlation_id"] == "env-trace"
