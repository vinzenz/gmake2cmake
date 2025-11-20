"""Centralized logging configuration module for gmake2cmake.

This module provides structured logging support with verbosity control,
complementing the existing diagnostic system.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, TextIO


def setup_logging(
    verbosity: int = 0,
    log_file: Optional[Path] = None,
    stream: Optional[TextIO] = None,
) -> None:
    """Configure logging with specified verbosity level.

    Args:
        verbosity: Verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3+=DEBUG)
        log_file: Optional path to write logs to file
        stream: Output stream for logging (defaults to stderr)

    Returns:
        None
    """
    stream = stream or sys.stderr

    # Map verbosity to log level
    if verbosity == 0:
        log_level = logging.ERROR
    elif verbosity == 1:
        log_level = logging.WARNING
    elif verbosity == 2:
        log_level = logging.INFO
    else:  # 3 or more
        log_level = logging.DEBUG

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(log_level)

    # Formatter - brief for normal use, detailed for debug
    if verbosity >= 3:
        formatter = logging.Formatter(
            fmt="%(levelname)s [%(name)s] %(message)s (%(filename)s:%(lineno)d)"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(levelname)s: %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s [%(name)s] %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as exc:  # pragma: no cover - file IO error
            root_logger.error(f"Failed to set up file logging: {exc}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_stage(stage_name: str, verbosity: int = 0) -> None:
    """Log the start of a pipeline stage.

    Args:
        stage_name: Name of the stage (e.g., 'discover', 'parse', 'evaluate')
        verbosity: Minimum verbosity level to display message

    Returns:
        None
    """
    logger = get_logger("gmake2cmake.pipeline")
    # Only log stages at verbosity level 2+ (INFO)
    if verbosity >= 2:
        logger.info(f"Starting pipeline stage: {stage_name}")
