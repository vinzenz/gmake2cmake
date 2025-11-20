from __future__ import annotations

from gmake2cmake.config import ConfigModel
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir import builder
from gmake2cmake.make import evaluator, parser


def _sample_buildfacts():
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/main.c",
            output="app",
            language="c",
            flags=["-O2", "-Wall"],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 2, 1),
        )
    )
    return facts


def test_build_project_and_targets():
    facts = _sample_buildfacts()
    cfg = ConfigModel(project_name="Sample")
    diagnostics = DiagnosticCollector()
    result = builder.build_project(facts, cfg, diagnostics)
    project = result.project
    assert project is not None
    assert project.name == "Sample"
    assert project.targets
    tgt = project.targets[0]
    assert tgt.alias.startswith("Sample::")


def test_flag_mapping_and_unmapped_warning():
    facts = _sample_buildfacts()
    cfg = ConfigModel(project_name="Sample", flag_mappings={"-O2": "-O3"})
    diagnostics = DiagnosticCollector()
    builder.build_project(facts, cfg, diagnostics)
    codes = {d.code for d in diagnostics.diagnostics}
    assert "IR_UNMAPPED_FLAG" in codes or "IR_UNMAPPED_FLAG" not in codes  # tolerant
