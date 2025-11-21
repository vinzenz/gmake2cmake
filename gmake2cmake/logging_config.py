"""Centralized structured logging configuration for gmake2cmake."""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, SysLogHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, TextIO

try:  # pragma: no cover - import shim for python-json-logger>=4
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # pragma: no cover - older versions
    from pythonjsonlogger.jsonlogger import JsonFormatter

LOG_LEVEL_ENV = "GMAKE2CMAKE_LOG_LEVEL"
CORRELATION_ID_ENV = "GMAKE2CMAKE_CORRELATION_ID"

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(JsonFormatter):
    """Add standard fields to every log record."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault(
            "timestamp", datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        )
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        log_record.setdefault("correlation_id", getattr(record, "correlation_id", None))
        log_record.setdefault("file", record.filename)
        log_record.setdefault("function", record.funcName)
        log_record.setdefault("line", record.lineno)


class CorrelationFilter(logging.Filter):
    """Inject correlation ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.correlation_id = get_correlation_id(generate=True)
        return True


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Assign a correlation ID for subsequent log records."""
    existing = _correlation_id.get()
    if correlation_id is None and existing:
        return existing
    resolved = correlation_id or os.getenv(CORRELATION_ID_ENV) or existing or uuid.uuid4().hex
    _correlation_id.set(resolved)
    return resolved


def get_correlation_id(generate: bool = False) -> Optional[str]:
    """Return the active correlation ID, creating one if requested."""
    existing = _correlation_id.get()
    if existing:
        return existing
    env_value = os.getenv(CORRELATION_ID_ENV)
    if env_value:
        _correlation_id.set(env_value)
        return env_value
    if generate:
        return set_correlation_id()
    return None


def reset_correlation_id() -> None:
    """Clear the correlation ID. Primarily used in tests."""
    _correlation_id.set(None)


def _resolve_log_level(verbosity: int) -> int:
    env_level = os.getenv(LOG_LEVEL_ENV)
    if env_level:
        level_map = logging.getLevelNamesMapping()
        normalized = env_level.strip().upper()
        if normalized in level_map:
            return level_map[normalized]
        if normalized.isdigit():
            return int(normalized)
    if verbosity == 0:
        return logging.ERROR
    if verbosity == 1:
        return logging.WARNING
    if verbosity == 2:
        return logging.INFO
    return logging.DEBUG


def _build_formatter() -> StructuredFormatter:
    return StructuredFormatter(
        json_indent=None,
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )


def _build_console_handler(level: int, stream: TextIO) -> logging.Handler:
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(level)
    return console_handler


def _build_file_handler(
    log_file: Path,
    level: int,
    *,
    max_bytes: int,
    backup_count: int,
    rotate_when: Optional[str],
    rotate_interval: int,
) -> Optional[logging.Handler]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if rotate_when:
        handler: logging.Handler = TimedRotatingFileHandler(
            log_file,
            when=rotate_when,
            interval=rotate_interval,
            backupCount=backup_count,
            encoding="utf-8",
        )
    elif max_bytes > 0:
        handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
    else:
        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    handler.setLevel(level)
    return handler


def _add_handler(
    root_logger: logging.Logger, handler: logging.Handler, formatter: logging.Formatter
) -> None:
    handler.addFilter(CorrelationFilter())
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def setup_logging(
    verbosity: int = 0,
    log_file: Optional[Path] = None,
    stream: Optional[TextIO] = None,
    *,
    max_bytes: int = 0,
    backup_count: int = 3,
    rotate_when: Optional[str] = None,
    rotate_interval: int = 1,
    syslog_address: Optional[str | tuple[str, int]] = None,
    correlation_id: Optional[str] = None,
) -> str:
    """Configure structured logging across console, file, and syslog.

    Args:
        verbosity: Verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3+=DEBUG)
        log_file: Optional path to write logs to file
        stream: Output stream for logging (defaults to stderr)
        max_bytes: Maximum bytes before rotating log_file (0 disables size rotation)
        backup_count: Number of rotated files to keep
        rotate_when: Timed rotation unit (e.g., 'midnight', 'H'); None disables timed rotation
        rotate_interval: Interval multiplier for timed rotation
        syslog_address: Optional syslog address (path or (host, port))
        correlation_id: Optional correlation ID (autogenerated if missing)

    Returns:
        The active correlation ID for this logging session.
    """
    stream = stream or sys.stderr
    resolved_correlation = set_correlation_id(correlation_id)
    log_level = _resolve_log_level(verbosity)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    formatter = _build_formatter()

    _add_handler(root_logger, _build_console_handler(log_level, stream), formatter)

    if log_file:
        try:
            file_handler = _build_file_handler(
                log_file,
                log_level,
                max_bytes=max_bytes,
                backup_count=backup_count,
                rotate_when=rotate_when,
                rotate_interval=rotate_interval,
            )
            if file_handler:
                _add_handler(root_logger, file_handler, formatter)
        except (OSError, PermissionError) as exc:  # pragma: no cover - file IO error
            root_logger.error(f"Failed to set up file logging: {exc}")

    if syslog_address:
        try:
            syslog_handler = SysLogHandler(address=syslog_address)
            syslog_handler.setLevel(log_level)
            _add_handler(root_logger, syslog_handler, formatter)
        except OSError:  # pragma: no cover - syslog unavailable
            root_logger.warning("Syslog unavailable at %s", syslog_address)

    return resolved_correlation


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)


def log_stage(
    stage_name: str,
    verbosity: int = 0,
    *,
    status: str = "start",
    duration_ms: float | None = None,
) -> None:
    """Emit a structured stage log entry."""
    if verbosity < 2:
        return
    logger = get_logger("gmake2cmake.pipeline")
    payload = {"event": "stage", "stage": stage_name, "status": status}
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 3)
    logger.info("pipeline stage", extra=payload)


@contextmanager
def log_timed_block(
    name: str,
    *,
    verbosity: int = 0,
    logger_name: str = "gmake2cmake.pipeline",
    level: int = logging.INFO,
):
    """Context manager that logs start/finish with duration for critical operations."""
    logger = get_logger(logger_name)
    status = "ok"
    start = time.perf_counter()
    if verbosity >= 2:
        logger.log(level, "start", extra={"event": "start", "operation": name})
    try:
        yield
    except Exception:
        status = "error"
        logger.error("operation failed", extra={"event": "error", "operation": name}, exc_info=True)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        if verbosity >= 1:
            logger.log(
                level,
                "complete",
                extra={
                    "event": "complete",
                    "operation": name,
                    "duration_ms": round(duration_ms, 3),
                    "status": status,
                },
            )
