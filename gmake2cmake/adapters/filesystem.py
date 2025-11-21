"""Filesystem adapter exports to keep IO at the boundary."""

from __future__ import annotations

from gmake2cmake.fs import (
    FileSystemAdapter,
    LocalFS,
    TestFileSystemAdapter,
    atomic_write,
    temporary_directory,
)

__all__ = [
    "FileSystemAdapter",
    "LocalFS",
    "TestFileSystemAdapter",
    "atomic_write",
    "temporary_directory",
]
