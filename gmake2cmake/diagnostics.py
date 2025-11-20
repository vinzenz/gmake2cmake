from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, TextIO

Severity = str


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    location: Optional[str] = None
    origin: Optional[str] = None


@dataclass
class DiagnosticCollector:
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
    diagnostic = Diagnostic(severity=severity, code=code, message=message, location=location, origin=origin)
    if _dedupe_key(diagnostic) in {_dedupe_key(d) for d in collector.diagnostics}:
        return
    collector.diagnostics.append(diagnostic)


def extend(collector: DiagnosticCollector, items: Iterable[Diagnostic]) -> None:
    for item in items:
        add(collector, item.severity, item.code, item.message, item.location, item.origin)


def has_errors(collector: DiagnosticCollector) -> bool:
    return any(d.severity == "ERROR" for d in collector.diagnostics)


def to_console(collector: DiagnosticCollector, *, stream: TextIO, verbose: bool) -> None:
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


def to_json(collector: DiagnosticCollector) -> str:
    payload = [
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
    return 1 if has_errors(collector) else 0
