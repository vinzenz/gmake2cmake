from __future__ import annotations

import json
from pathlib import Path

from gmake2cmake.diagnostics import DiagnosticCollector, to_json
from gmake2cmake.make import discovery
from tests.conftest import FakeFS


def test_discovery_missing_include_captures_line_text():
    fs = FakeFS()
    root = Path("/proj/Makefile")
    fs.store[root] = "include missing.mk\nall:\n\techo hi\n"

    diagnostics = DiagnosticCollector()
    discovery.discover(root.parent, None, fs, diagnostics)

    diag = next(d for d in diagnostics.diagnostics if d.code == "DISCOVERY_INCLUDE_MISSING")
    assert diag.line.strip() == "include missing.mk"

    payload = json.loads(to_json(diagnostics))
    include_entry = next(item for item in payload if item["code"] == "DISCOVERY_INCLUDE_MISSING")
    assert include_entry["line"].startswith("include missing.mk")
