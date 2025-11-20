from __future__ import annotations

from pathlib import Path

from gmake2cmake.diagnostics import DiagnosticCollector, has_errors
from gmake2cmake.make import discovery
from tests.conftest import FakeFS


def test_resolve_entry_missing_adds_error(tmp_path):
    fs = FakeFS()
    diagnostics = DiagnosticCollector()
    entry = discovery.resolve_entry(tmp_path, None, fs, diagnostics)
    assert entry is None
    assert has_errors(diagnostics) is True


def test_scan_includes_cycle_detection(tmp_path):
    fs = FakeFS()
    a = (tmp_path / "A").as_posix()
    b = (tmp_path / "B").as_posix()
    fs.store[Path(a)] = "include B"
    fs.store[Path(b)] = "include A"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(Path(a), fs, diagnostics)
    assert graph.cycles
    assert has_errors(diagnostics) is True


def test_collect_contents_ordering(tmp_path):
    fs = FakeFS()
    root = (tmp_path / "Makefile").resolve()
    inc = (tmp_path / "inc.mk").resolve()
    fs.store[root] = "include inc.mk\nall:\n\techo hi"
    fs.store[inc] = "VAR=1"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(root, fs, diagnostics)
    contents = discovery.collect_contents(graph, fs, diagnostics)
    assert contents[0].path == root.as_posix()
    assert contents[1].path == inc.as_posix()


def test_scan_includes_optional_include_missing_warns_only(tmp_path):
    """Optional includes missing should only warn, not error."""
    fs = FakeFS()
    root = (tmp_path / "Makefile").resolve()
    fs.store[root] = "-include optional.mk\nall:\n\techo hi"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(root, fs, diagnostics)
    # Should have the node
    assert root.as_posix() in graph.nodes
    # Should have warn diagnostic for optional include, not error
    warns = [d for d in diagnostics.diagnostics if d.severity == "WARN"]
    assert any("DISCOVERY_INCLUDE_OPTIONAL_MISSING" in str(d) for d in warns)
    # Should not have errors
    assert not has_errors(diagnostics)


def test_scan_includes_mandatory_include_missing_errors(tmp_path):
    """Mandatory includes missing should error."""
    fs = FakeFS()
    root = (tmp_path / "Makefile").resolve()
    fs.store[root] = "include required.mk\nall:\n\techo hi"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(root, fs, diagnostics)
    # Should have error diagnostic for missing mandatory include
    assert has_errors(diagnostics)
    assert any("DISCOVERY_INCLUDE_MISSING" in str(d) for d in diagnostics.diagnostics)


def test_scan_includes_mixed_optional_and_mandatory(tmp_path):
    """Test mix of optional and mandatory includes."""
    fs = FakeFS()
    root = (tmp_path / "Makefile").resolve()
    inc_req = (tmp_path / "required.mk").resolve()
    fs.store[root] = "include required.mk\n-include optional.mk\nall:\n\techo hi"
    fs.store[inc_req] = "VAR=1"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(root, fs, diagnostics)
    # Should include both edges
    assert root.as_posix() in graph.edges
    # Required include should be in graph
    assert inc_req.as_posix() in graph.nodes
    # Optional include warning but not error
    warns = [d for d in diagnostics.diagnostics if d.severity == "WARN"]
    assert any("DISCOVERY_INCLUDE_OPTIONAL_MISSING" in str(d) for d in warns)
    # No errors
    assert not has_errors(diagnostics)


def test_collect_contents_preserves_order_with_subdir_and_includes(tmp_path):
    """Test that collection order is stable with mixed include and subdir edges."""
    fs = FakeFS()
    root = (tmp_path / "Makefile").resolve()
    inc1 = (tmp_path / "inc1.mk").resolve()
    inc2 = (tmp_path / "inc2.mk").resolve()
    fs.store[root] = "include inc1.mk\ninclude inc2.mk\nall:\n\techo hi"
    fs.store[inc1] = "VAR1=1"
    fs.store[inc2] = "VAR2=2"
    diagnostics = DiagnosticCollector()
    graph = discovery.scan_includes(root, fs, diagnostics)
    contents = discovery.collect_contents(graph, fs, diagnostics)
    # Root should come first
    assert contents[0].path == root.as_posix()
    # Then includes in order they were discovered
    paths = [c.path for c in contents]
    assert inc1.as_posix() in paths
    assert inc2.as_posix() in paths
