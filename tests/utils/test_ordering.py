"""Tests for deterministic ordering utilities."""

from __future__ import annotations

import pytest

from gmake2cmake.utils.ordering import (
    dependency_sort,
    natural_sort,
    sort_diagnostics,
    sort_files,
    stable_sort,
    topological_sort,
)


def test_stable_sort_basic():
    """Test basic stable sorting."""
    items = [3, 1, 2, 1, 3]
    result = stable_sort(items)
    assert result == [1, 1, 2, 3, 3]


def test_stable_sort_with_key():
    """Test stable sort with custom key."""
    items = [(2, "b"), (1, "a"), (1, "c")]
    result = stable_sort(items, key=lambda x: x[0])
    assert result == [(1, "a"), (1, "c"), (2, "b")]


def test_stable_sort_deterministic():
    """Test that stable sort is deterministic."""
    items = [5, 2, 8, 2, 5, 1]
    result1 = stable_sort(items)
    result2 = stable_sort(items)
    assert result1 == result2


def test_topological_sort_simple():
    """Test simple topological sort."""
    # A depends on B, B depends on C
    graph = {"A": {"B"}, "B": {"C"}, "C": set()}
    result = topological_sort(graph)
    # C should come first, then B, then A
    assert result.index("C") < result.index("B")
    assert result.index("B") < result.index("A")


def test_topological_sort_partial_order():
    """Test topological sort with partial order."""
    # A depends on B and C
    # D has no dependencies
    graph = {"A": {"B", "C"}, "B": set(), "C": set(), "D": set()}
    result = topological_sort(graph)
    assert result.index("B") < result.index("A")
    assert result.index("C") < result.index("A")
    # D can be anywhere


def test_topological_sort_cycle_detection():
    """Test cycle detection in topological sort."""
    # A -> B -> C -> A (cycle)
    graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    with pytest.raises(ValueError, match="Cycle detected"):
        topological_sort(graph)


def test_topological_sort_deterministic():
    """Test that topological sort is deterministic."""
    graph = {"A": set(), "B": set(), "C": set()}
    result1 = topological_sort(graph)
    result2 = topological_sort(graph)
    assert result1 == result2


def test_natural_sort_basic():
    """Test natural sort with mixed numeric/alpha."""
    items = ["file10", "file2", "file1"]
    result = natural_sort(items)
    assert result == ["file1", "file2", "file10"]


def test_natural_sort_with_key():
    """Test natural sort with custom key."""
    items = ["a10", "a2", "a1", "b5"]
    result = natural_sort(items, key=lambda x: x)
    assert result[0] == "a1"
    assert result[1] == "a2"
    assert result[2] == "a10"


def test_natural_sort_deterministic():
    """Test that natural sort is deterministic."""
    items = ["ver3.1", "ver1.0", "ver2.5", "ver3.1"]
    result1 = natural_sort(items)
    result2 = natural_sort(items)
    assert result1 == result2


def test_dependency_sort_simple():
    """Test dependency sort."""
    items = ["A", "B", "C"]
    dep_graph = {"A": {"B"}, "B": {"C"}, "C": set()}
    result = dependency_sort(items, dep_graph)
    assert result.index("C") < result.index("B")
    assert result.index("B") < result.index("A")


def test_dependency_sort_cycle_detection():
    """Test cycle detection in dependency sort."""
    items = ["A", "B", "C"]
    dep_graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    with pytest.raises(ValueError, match="Circular dependency"):
        dependency_sort(items, dep_graph)


def test_sort_diagnostics_by_severity():
    """Test diagnostic sorting by severity."""

    class MockDiagnostic:
        def __init__(self, severity, code, message):
            self.severity = severity
            self.code = code
            self.message = message

    diags = [
        MockDiagnostic("INFO", "I1", "info message"),
        MockDiagnostic("ERROR", "E1", "error message"),
        MockDiagnostic("WARN", "W1", "warning message"),
    ]

    result = sort_diagnostics(diags)
    assert result[0].severity == "ERROR"
    assert result[1].severity == "WARN"
    assert result[2].severity == "INFO"


def test_sort_diagnostics_deterministic():
    """Test that diagnostic sorting is deterministic."""

    class MockDiagnostic:
        def __init__(self, severity, code, message):
            self.severity = severity
            self.code = code
            self.message = message

    diags1 = [
        MockDiagnostic("WARN", "W1", "msg"),
        MockDiagnostic("ERROR", "E1", "msg"),
        MockDiagnostic("WARN", "W2", "msg"),
    ]
    diags2 = [
        MockDiagnostic("WARN", "W2", "msg"),
        MockDiagnostic("ERROR", "E1", "msg"),
        MockDiagnostic("WARN", "W1", "msg"),
    ]

    result1 = sort_diagnostics(diags1)
    result2 = sort_diagnostics(diags2)

    assert [(d.code, d.severity) for d in result1] == [(d.code, d.severity) for d in result2]


def test_sort_files_natural_order():
    """Test file sorting with natural ordering."""
    files = ["src/main.c", "src/file10.c", "src/file2.c", "include/header.h"]
    result = sort_files(files)
    # Should sort naturally
    assert result.index("src/file2.c") < result.index("src/file10.c")


def test_sort_files_deterministic():
    """Test that file sorting is deterministic."""
    files = ["z.c", "a.c", "m.c", "b.c"]
    result1 = sort_files(files)
    result2 = sort_files(files)
    assert result1 == result2


def test_topological_sort_with_explicit_nodes():
    """Test topological sort with explicitly provided nodes."""
    graph = {"A": {"B"}, "B": set()}
    all_nodes = {"A", "B", "C"}  # C is isolated
    result = topological_sort(graph, all_nodes)
    assert len(result) == 3
    assert "C" in result
    assert result.index("B") < result.index("A")


def test_stable_sort_preserves_equal_elements():
    """Test that stable sort preserves order of equal elements."""

    class Item:
        def __init__(self, key, value):
            self.key = key
            self.value = value

    items = [Item(1, "a"), Item(2, "b"), Item(1, "c"), Item(2, "d")]
    result = stable_sort(items, key=lambda x: x.key)

    # Items with key=1 should maintain order: a, c
    # Items with key=2 should maintain order: b, d
    assert result[0].value == "a"
    assert result[1].value == "c"
    assert result[2].value == "b"
    assert result[3].value == "d"
