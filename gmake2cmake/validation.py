"""Central validation helpers for user-provided inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.path_utils import validate_path
from gmake2cmake.security import SecurityError, sanitize_command_arg, validate_identifier

MAX_INPUT_LENGTH = 4096
MAX_CONFIG_BYTES = 2 * 1024 * 1024  # 2MB hard limit for config files


def _record_error(code: str, diagnostics: DiagnosticCollector, message: str, location: Optional[str] = None) -> None:
    add(diagnostics, "ERROR", code, message, location)


def validate_cli_args(cli_args, diagnostics: DiagnosticCollector) -> None:
    """Validate CLI arguments for traversal, size, and suspicious characters."""
    _validate_path_field(cli_args.source_dir, "source_dir", diagnostics, allow_traversal=True)
    _validate_path_field(cli_args.output_dir, "output_dir", diagnostics, allow_traversal=True)
    if cli_args.log_file:
        _validate_path_field(cli_args.log_file, "log_file", diagnostics, allow_traversal=True)
    if cli_args.entry_makefile:
        _validate_path_field(cli_args.entry_makefile, "entry_makefile", diagnostics, allow_traversal=False)
    if cli_args.config_path:
        _validate_path_field(cli_args.config_path, "config_path", diagnostics, allow_traversal=True)
    if cli_args.processes is not None and cli_args.processes < 0:
        _record_error("VALIDATION_INVALID_VALUE", diagnostics, "processes cannot be negative")
    _sanitize_freeform_arg(getattr(cli_args, "namespace", None), "namespace", diagnostics)


def _validate_path_field(value, field: str, diagnostics: DiagnosticCollector, *, allow_traversal: bool) -> None:
    text = str(value)
    if len(text) > MAX_INPUT_LENGTH:
        _record_error("VALIDATION_PATH", diagnostics, f"{field} exceeds maximum length ({MAX_INPUT_LENGTH})", text)
        return
    try:
        validate_path(text, allow_empty=False, allow_traversal=allow_traversal)
    except ValueError as exc:
        _record_error("VALIDATION_PATH", diagnostics, f"{field}: {exc}", text)


def validate_identifier_field(value: Optional[str], field: str, diagnostics: DiagnosticCollector, *, max_length: int = 256) -> Optional[str]:
    """Validate identifier-like fields (namespaces, project names)."""
    if value is None:
        return None
    if len(value) > MAX_INPUT_LENGTH:
        _record_error("VALIDATION_IDENTIFIER", diagnostics, f"{field} length exceeds limit ({MAX_INPUT_LENGTH})", value)
        return None
    try:
        return validate_identifier(value, max_length=max_length)
    except SecurityError as exc:
        _record_error("VALIDATION_IDENTIFIER", diagnostics, f"{field}: {exc}", value)
        return None


def enforce_size_limit(text: str, path: Path, diagnostics: DiagnosticCollector, *, max_bytes: int = MAX_CONFIG_BYTES, code: str = "CONFIG_TOO_LARGE") -> bool:
    """Ensure a text blob does not exceed a byte threshold."""
    size = len(text.encode("utf-8", errors="ignore"))
    if size > max_bytes:
        _record_error(code, diagnostics, f"{path} exceeds allowed size ({size} bytes > {max_bytes} bytes)", str(path))
        return False
    return True


def _sanitize_freeform_arg(value: Optional[str], field: str, diagnostics: DiagnosticCollector) -> None:
    if value is None:
        return
    try:
        sanitize_command_arg(value)
    except SecurityError as exc:
        _record_error("VALIDATION_INVALID_VALUE", diagnostics, f"{field}: {exc}", value)
