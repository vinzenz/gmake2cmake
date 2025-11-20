from __future__ import annotations

from pathlib import Path

from gmake2cmake.cmake import emitter
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir import builder


def test_emit_root_and_global_module(tmp_path):
    project = builder.Project(
        name="Demo",
        version=None,
        namespace="Demo",
        languages=["C"],
        targets=[],
        project_config=builder.ProjectGlobalConfig(
            vars={"OPT": "1"},
            flags={"c": ["-O2"]},
            defines=[],
            includes=["inc"],
            feature_toggles={},
            sources=["config.mk"],
        ),
    )
    options = emitter.EmitOptions(dry_run=False, packaging=False, namespace="Demo")
    diagnostics = DiagnosticCollector()
    class FS:
        def __init__(self):
            self.writes = {}
        def makedirs(self, path): path.mkdir(parents=True, exist_ok=True)
        def write_text(self, path, data): self.writes[path] = data
    fs = FS()
    generated = emitter.emit(project, tmp_path, options=options, fs=fs, diagnostics=diagnostics)
    paths = [Path(g.path).name for g in generated]
    assert "CMakeLists.txt" in paths
    assert "ProjectGlobalConfig.cmake" in paths
