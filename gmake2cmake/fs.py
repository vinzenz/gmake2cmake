from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class FileSystemAdapter(Protocol):
    def read_text(self, path: Path) -> str: ...

    def write_text(self, path: Path, data: str) -> None: ...

    def exists(self, path: Path) -> bool: ...

    def is_file(self, path: Path) -> bool: ...

    def makedirs(self, path: Path) -> None: ...


@dataclass
class LocalFS:
    """Thin wrapper around pathlib for testability."""

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, data: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def makedirs(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
