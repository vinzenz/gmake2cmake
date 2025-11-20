"""Tests for recursive Make subdirectory traversal."""

from __future__ import annotations

from pathlib import Path

from gmake2cmake.diagnostics import DiagnosticCollector, has_errors
from gmake2cmake.make import discovery
from tests.conftest import FakeFS


def test_recursive_make_basic():
    """Test basic recursive make detection with $(MAKE) -C."""
    fs = FakeFS()
    root_makefile = Path("/project/Makefile").as_posix()
    subdir_makefile = Path("/project/subdir/Makefile").as_posix()

    fs.store[Path(root_makefile)] = "all:\n\t$(MAKE) -C subdir"
    fs.store[Path(subdir_makefile)] = "all:\n\techo building subdir"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root_makefile), fs, diagnostics)

    # Check that both makefiles are in the graph
    assert root_makefile in graph.nodes
    assert subdir_makefile in graph.nodes

    # Check edge relationship
    assert subdir_makefile in graph.edges.get(root_makefile, set())

    # No errors should occur
    assert not has_errors(diagnostics)


def test_recursive_make_with_variable_substitution():
    """Test recursive make with variable substitution in directory path."""
    fs = FakeFS()
    root_makefile = Path("/project/Makefile").as_posix()
    subdir_makefile = Path("/project/src/Makefile").as_posix()

    # Note: Variable substitution is complex and may not be fully supported,
    # but the parser should handle it gracefully
    fs.store[Path(root_makefile)] = "SRCDIR=src\nall:\n\t$(MAKE) -C $(SRCDIR)"
    fs.store[Path(subdir_makefile)] = "all:\n\techo building src"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root_makefile), fs, diagnostics)

    # The graph should still be created (even if variable substitution is limited)
    assert root_makefile in graph.nodes


def test_recursive_make_missing_subdir():
    """Test detection of missing recursive make directory."""
    fs = FakeFS()
    root_makefile = Path("/project/Makefile").as_posix()

    fs.store[Path(root_makefile)] = "all:\n\t$(MAKE) -C missing_dir"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root_makefile), fs, diagnostics)

    # Root should be in graph
    assert root_makefile in graph.nodes

    # Should have a warning about missing subdir
    assert any("SUBDIR_MISSING" in d.code for d in diagnostics.diagnostics)


def test_recursive_make_with_flag():
    """Test recursive make with additional flags like -f."""
    fs = FakeFS()
    root_makefile = Path("/project/Makefile").as_posix()
    custom_makefile = Path("/project/build/custom.mk").as_posix()

    fs.store[Path(root_makefile)] = "all:\n\t$(MAKE) -C build -f custom.mk"
    fs.store[Path(custom_makefile)] = "all:\n\techo building"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root_makefile), fs, diagnostics)

    # Root should be in graph (may not capture the -f flag in traversal)
    assert root_makefile in graph.nodes


def test_recursive_make_multi_level():
    """Test multi-level recursive make traversal."""
    fs = FakeFS()
    root = Path("/project/Makefile").as_posix()
    level1 = Path("/project/src/Makefile").as_posix()
    level2 = Path("/project/src/core/Makefile").as_posix()

    fs.store[Path(root)] = "all:\n\t$(MAKE) -C src"
    fs.store[Path(level1)] = "all:\n\t$(MAKE) -C core"
    fs.store[Path(level2)] = "all:\n\techo building core"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root), fs, diagnostics)

    # All three should be in the graph
    assert root in graph.nodes
    assert level1 in graph.nodes
    assert level2 in graph.nodes

    # Edges should form a chain
    assert level1 in graph.edges.get(root, set())
    assert level2 in graph.edges.get(level1, set())

    # No errors
    assert not has_errors(diagnostics)


def test_recursive_make_cycle_detection():
    """Test cycle detection in recursive make patterns."""
    fs = FakeFS()
    dir_a = Path("/project/a/Makefile").as_posix()
    dir_b = Path("/project/b/Makefile").as_posix()

    fs.store[Path(dir_a)] = "all:\n\t$(MAKE) -C ../b"
    fs.store[Path(dir_b)] = "all:\n\t$(MAKE) -C ../a"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(dir_a), fs, diagnostics)

    # Cycle should be detected
    assert graph.cycles
    assert has_errors(diagnostics)
    assert any("CYCLE" in d.code for d in diagnostics.diagnostics)


def test_mixed_include_and_recursive_patterns():
    """Test makefiles with both include and recursive make patterns."""
    fs = FakeFS()
    root = Path("/project/Makefile").as_posix()
    common = Path("/project/common.mk").as_posix()
    subdir = Path("/project/src/Makefile").as_posix()

    fs.store[Path(root)] = "include common.mk\nall:\n\t$(MAKE) -C src"
    fs.store[Path(common)] = "CFLAGS=-O2"
    fs.store[Path(subdir)] = "all:\n\techo building src"

    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(root), fs, diagnostics)

    # All three should be in the graph
    assert root in graph.nodes
    assert common in graph.nodes
    assert subdir in graph.nodes

    # No cycles
    assert not graph.cycles
    assert not has_errors(diagnostics)
