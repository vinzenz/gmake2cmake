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
