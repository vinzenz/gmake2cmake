"""Type definitions for gmake2cmake.

This package provides shared type definitions and TypedDicts for improved type safety and IDE support.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class DiagnosticDict(TypedDict, total=False):
    """Typed dictionary for diagnostic message payloads."""

    severity: str
    code: str
    message: str
    location: Optional[str]
    origin: Optional[str]


__all__ = ["DiagnosticDict"]
