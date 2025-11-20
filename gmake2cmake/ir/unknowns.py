from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _truncate(text: str, max_len: int = 160) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _fallback_normalized(raw: str, normalized: Optional[str]) -> str:
    if normalized and normalized.strip():
        return normalized.strip()
    return raw


def _format_uc_id(counter: int) -> str:
    return f"UC{counter:04d}"


@dataclass
class UnknownConstruct:
    id: str
    category: str
    file: str
    line: Optional[int]
    column: Optional[int]
    raw_snippet: str
    normalized_form: str
    context: Dict[str, List[str]] = field(default_factory=dict)
    impact: Dict[str, str] = field(default_factory=dict)
    cmake_status: str = "not_generated"
    suggested_action: str = "manual_review"


class UnknownConstructFactory:
    def __init__(self) -> None:
        self._counter = 1

    def create(
        self,
        *,
        category: str,
        file: str,
        raw_snippet: str,
        normalized_form: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        context: Optional[Dict[str, List[str]]] = None,
        impact: Optional[Dict[str, str]] = None,
        cmake_status: str = "not_generated",
        suggested_action: str = "manual_review",
    ) -> UnknownConstruct:
        uc = UnknownConstruct(
            id=_format_uc_id(self._counter),
            category=category,
            file=file,
            line=line,
            column=column,
            raw_snippet=_truncate(raw_snippet),
            normalized_form=_truncate(_fallback_normalized(raw_snippet, normalized_form)),
            context=context or {},
            impact=impact or {},
            cmake_status=cmake_status,
            suggested_action=suggested_action,
        )
        self._counter += 1
        return uc


def to_dict(uc: UnknownConstruct) -> Dict:
    payload = {
        "id": uc.id,
        "category": uc.category,
        "file": uc.file,
        "line": uc.line,
        "column": uc.column,
        "raw_snippet": uc.raw_snippet,
        "normalized_form": uc.normalized_form,
        "context": uc.context,
        "impact": uc.impact,
        "cmake_status": uc.cmake_status,
        "suggested_action": uc.suggested_action,
    }
    return payload
