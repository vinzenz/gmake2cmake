"""Type definitions for gmake2cmake.

This module provides shared type definitions and TypedDicts for improved type safety and IDE support.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class DiagnosticDict(TypedDict, total=False):
    """Typed dictionary for diagnostic message payloads.

    Attributes:
        severity: Severity level ('ERROR', 'WARN', 'INFO')
        code: Diagnostic code identifier
        message: Human-readable diagnostic message
        location: Optional file:line or file:line:column location
        origin: Optional origin module identifier
    """

    severity: str
    code: str
    message: str
    location: Optional[str]
    origin: Optional[str]
