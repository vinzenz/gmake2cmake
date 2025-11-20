from __future__ import annotations

from gmake2cmake.config import ConfigModel, LinkOverride
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
    assert "IR_UNMAPPED_FLAG" in codes


def test_internal_dependency_uses_alias():
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/libfoo.c",
            output="libfoo.a",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/main.c",
            output="app",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 2, 1),
        )
    )
    facts.rules.append(
        evaluator.EvaluatedRule(
            targets=["app"],
            prerequisites=["libfoo.a"],
            commands=[],
            is_pattern=False,
            location=parser.SourceLocation("Makefile", 2, 1),
        )
    )
    cfg = ConfigModel(project_name="Demo", namespace="Demo")
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    lib = next(t for t in project.targets if t.artifact == "libfoo.a")
    app = next(t for t in project.targets if t.artifact == "app")
    assert lib.alias == "Demo::libfoo"
    assert app.deps == ["Demo::libfoo"]


def test_external_override_disables_alias():
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/libfoo.c",
            output="libfoo.a",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    cfg = ConfigModel(project_name="Demo", namespace="Demo", link_overrides={"libfoo": LinkOverride(classification="external")})
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    lib = project.targets[0]
    assert lib.alias is None


def test_imported_override_creates_imported_target():
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/z.c",
            output="libz.a",
            language="c",
            flags=[],
            includes=["include"],
            defines=["ZDEF"],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    cfg = ConfigModel(project_name="Demo", namespace="Demo", link_overrides={"libz": LinkOverride(classification="imported", imported_target="Zlib::Z", alias="Zlib::Z")})
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    target = project.targets[0]
    assert target.type == "imported"
    assert target.name == "Zlib::Z"
    assert target.sources == []
    assert target.alias == "Zlib::Z"


def test_compile_includes_and_defines_propagated():
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/a.c",
            output="liba.a",
            language="c",
            flags=["-Wall"],
            includes=["inc/a"],
            defines=["A_DEF"],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    cfg = ConfigModel(project_name="Demo")
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    tgt = project.targets[0]
    assert "inc/a" in tgt.include_dirs
    assert "A_DEF" in tgt.defines
