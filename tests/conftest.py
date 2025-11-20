from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeFS:
    def __init__(self) -> None:
        self.store: dict[Path, str] = {}
        self.writes: list[Path] = []

    def read_text(self, path: Path) -> str:
        return self.store[path]

    def write_text(self, path: Path, data: str) -> None:
        self.writes.append(path)
        self.store[path] = data

    def exists(self, path: Path) -> bool:
        return path in self.store

    def is_file(self, path: Path) -> bool:
        return path in self.store

    def makedirs(self, path: Path) -> None:
        # No-op for fake filesystem
        return None
