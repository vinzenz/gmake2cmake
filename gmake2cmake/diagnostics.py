from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, List, Optional, TextIO

from gmake2cmake.constants import VALID_DIAGNOSTIC_SEVERITIES
from gmake2cmake.types import DiagnosticDict

if TYPE_CHECKING:
    pass

Severity = str


@dataclass(frozen=True)
class Diagnostic:
    """A single diagnostic message with severity, code, and location.

    Attributes:
        severity: One of 'ERROR', 'WARN', 'INFO'
        code: Diagnostic code identifier
        message: Human-readable message
        location: Optional file:line:column location
        origin: Optional origin module identifier
    """

    severity: Severity
    code: str
    message: str
    location: Optional[str] = None
    origin: Optional[str] = None

    def __post_init__(self) -> None:
        if self.severity not in VALID_DIAGNOSTIC_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")
        if not self.code or not self.code.strip():
            raise ValueError("code cannot be empty")
        if not self.message or not self.message.strip():
            raise ValueError("message cannot be empty")
        # Validate code is registered (lazy import to avoid circular dependency)
        from gmake2cmake.diagnostic_codes import is_valid_code
        if not is_valid_code(self.code):
            raise ValueError(f"Invalid diagnostic code: {self.code}. Use DiagnosticCode enum for valid codes.")


@dataclass
class DiagnosticCollector:
    """Collects diagnostic messages during pipeline execution.

    Attributes:
        diagnostics: List of accumulated Diagnostic messages
    """

    diagnostics: List[Diagnostic] = field(default_factory=list)


_SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


def _dedupe_key(d: Diagnostic) -> tuple:
    return (d.severity, d.code, d.message, d.location, d.origin)


def add(
    collector: DiagnosticCollector,
    severity: Severity,
    code: str,
    message: str,
    location: Optional[str] = None,
    origin: Optional[str] = None,
) -> None:
    """Add a diagnostic to the collector, deduplicating identical entries.

    Args:
        collector: DiagnosticCollector instance to add to
        severity: Severity level ('ERROR', 'WARN', 'INFO')
        code: Diagnostic code identifier
        message: Human-readable diagnostic message
        location: Optional file:line:column location
        origin: Optional origin module identifier

    Returns:
        None
    """
    diagnostic = Diagnostic(severity=severity, code=code, message=message, location=location, origin=origin)
    if _dedupe_key(diagnostic) in {_dedupe_key(d) for d in collector.diagnostics}:
        return
    collector.diagnostics.append(diagnostic)


def extend(collector: DiagnosticCollector, items: Iterable[Diagnostic]) -> None:
    """Extend collector with multiple diagnostics.

    Args:
        collector: DiagnosticCollector instance to extend
        items: Iterable of Diagnostic instances to add

    Returns:
        None
    """
    for item in items:
        add(collector, item.severity, item.code, item.message, item.location, item.origin)


def has_errors(collector: DiagnosticCollector) -> bool:
    """Check if collector contains any ERROR diagnostics.

    Args:
        collector: DiagnosticCollector instance to check

    Returns:
        True if any ERROR severity diagnostics exist, False otherwise
    """
    return any(d.severity == "ERROR" for d in collector.diagnostics)


def to_console(collector: DiagnosticCollector, *, stream: TextIO, verbose: bool, unknown_count: int = 0) -> None:
    """Write diagnostics to console in human-readable format.

    Args:
        collector: DiagnosticCollector instance to output
        stream: Output stream to write to
        verbose: If True, include origin information
        unknown_count: Number of unknown constructs to report

    Returns:
        None
    """
    ordered = sorted(
        collector.diagnostics, key=lambda d: (_SEVERITY_ORDER.get(d.severity, 99), d.code, d.message)
    )
    for diag in ordered:
        parts = [f"[{diag.severity}] {diag.code}: {diag.message}"]
        if diag.location:
            parts[-1] += f" ({diag.location})"
        if verbose and diag.origin:
            parts[-1] += f" [{diag.origin}]"
        stream.write(parts[-1] + "\n")
    if unknown_count:
        stream.write(f"{unknown_count} unknown constructs (see report for details).\n")


def to_json(collector: DiagnosticCollector) -> str:
    """Serialize diagnostics to JSON with stable key ordering.

    Args:
        collector: DiagnosticCollector instance to serialize

    Returns:
        JSON string with diagnostics array

    """
    payload: list[DiagnosticDict] = [
        {
            "severity": d.severity,
            "code": d.code,
            "message": d.message,
            "location": d.location,
            "origin": d.origin,
        }
        for d in collector.diagnostics
    ]
    return json.dumps(payload, sort_keys=True)


def exit_code(collector: DiagnosticCollector) -> int:
    """Get exit code for diagnostics using category-specific exit codes.

    Returns the appropriate exit code based on diagnostic categories.
    This function delegates to the exit_codes module for category mapping.

    Args:
        collector: DiagnosticCollector instance containing diagnostics

    Returns:
        Exit code (0-5) indicating success or failure category
    """
    from gmake2cmake.exit_codes import get_exit_code
    return get_exit_code(collector)
