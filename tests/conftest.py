"""Pytest configuration and shared fixtures for gmake2cmake tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gmake2cmake.cache import CacheConfig, EvaluationCache  # noqa: E402
from gmake2cmake.diagnostics import DiagnosticCollector  # noqa: E402
from gmake2cmake.fs import LocalFS  # noqa: E402


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


# ============================================================================
# Pytest Fixtures for Test Coverage (TASK-0059)
# ============================================================================


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with basic structure."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "build").mkdir()
    return project


@pytest.fixture
def fs_adapter() -> LocalFS:
    """Provide a real filesystem adapter."""
    return LocalFS()


@pytest.fixture
def diagnostic_collector() -> DiagnosticCollector:
    """Provide a diagnostic collector for tests."""
    return DiagnosticCollector()


@pytest.fixture
def evaluation_cache() -> EvaluationCache:
    """Provide an evaluation cache for tests."""
    config = CacheConfig(enabled=True, max_size=256)
    return EvaluationCache(config)


@pytest.fixture
def cache_disabled() -> EvaluationCache:
    """Provide a disabled evaluation cache for testing fallback behavior."""
    config = CacheConfig(enabled=False)
    return EvaluationCache(config)


@pytest.fixture
def makefile_simple() -> str:
    """Provide a simple test Makefile."""
    return """
.PHONY: all clean

SRCS = main.c lib.c
OBJS = $(SRCS:.c=.o)
TARGET = program

all: $(TARGET)

$(TARGET): $(OBJS)
\tgcc -o $@ $^

%.o: %.c
\tgcc -c $<

clean:
\trm -f $(OBJS) $(TARGET)
"""


@pytest.fixture
def makefile_complex() -> str:
    """Provide a complex Makefile with variables and patterns."""
    return """
# Configuration
CC = gcc
CFLAGS = -Wall -O2 -DDEBUG
LDFLAGS = -lm

# Directories
SRCDIR = src
OBJDIR = build
BINDIR = bin

# Source files
SRCS = $(wildcard $(SRCDIR)/*.c)
OBJS = $(SRCS:$(SRCDIR)/%.c=$(OBJDIR)/%.o)
BINS = $(OBJS:$(OBJDIR)/%.o=$(BINDIR)/%)

# Targets
all: $(BINS)

$(BINDIR)/%: $(OBJDIR)/%.o
\t@mkdir -p $(BINDIR)
\t$(CC) $(LDFLAGS) -o $@ $<

$(OBJDIR)/%.o: $(SRCDIR)/%.c
\t@mkdir -p $(OBJDIR)
\t$(CC) $(CFLAGS) -c -o $@ $<

clean:
\trm -rf $(OBJDIR) $(BINDIR)

.PHONY: all clean
"""


@pytest.fixture
def fake_fs() -> FakeFS:
    """Provide a fake filesystem for testing without I/O."""
    return FakeFS()
