from __future__ import annotations

import pytest

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


def test_external_target_alias_assignment():
    """Regression test for external target alias assignment (with and without overrides)."""
    # Test 1: External target without override (absolute path) should have no alias
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="/usr/src/libfoo.c",
            output="/usr/lib/libfoo.a",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    cfg = ConfigModel(project_name="Demo", namespace="Demo")
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    target = project.targets[0]
    assert target.alias is None, "External target without override should not have alias"

    # Test 2: External target with override specifying no alias should have no alias
    facts2 = evaluator.BuildFacts()
    facts2.inferred_compiles.append(
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
    cfg2 = ConfigModel(
        project_name="Demo",
        namespace="Demo",
        link_overrides={"libfoo": LinkOverride(classification="external")}
    )
    diagnostics2 = DiagnosticCollector()
    project2 = builder.build_project(facts2, cfg2, diagnostics2).project
    assert project2 is not None
    target2 = project2.targets[0]
    assert target2.alias is None, "External override without alias should not have alias"

    # Test 3: External target with override specifying an alias should use that alias
    cfg3 = ConfigModel(
        project_name="Demo",
        namespace="Demo",
        link_overrides={"libfoo": LinkOverride(classification="external", alias="Custom::Alias")}
    )
    diagnostics3 = DiagnosticCollector()
    project3 = builder.build_project(facts2, cfg3, diagnostics3).project
    assert project3 is not None
    target3 = project3.targets[0]
    assert target3.alias == "Custom::Alias", "External override with alias should use that alias"


def test_source_file_validation():
    # Valid source file
    sf = builder.SourceFile(path="src/main.c", language="c", flags=["-O2"])
    assert sf.path == "src/main.c"

    # Invalid: empty path
    with pytest.raises(ValueError, match="path cannot be empty"):
        builder.SourceFile(path="", language="c", flags=[])

    # Invalid: empty language
    with pytest.raises(ValueError, match="language cannot be empty"):
        builder.SourceFile(path="file.c", language="", flags=[])


def test_target_validation():
    # Valid target
    tgt = builder.Target(
        artifact="lib.a",
        name="my_lib",
        alias="Project::MyLib",
        type="static",
        sources=[],
        include_dirs=[],
        defines=[],
        compile_options=[],
        link_options=[],
        link_libs=[],
        deps=[],
    )
    assert tgt.artifact == "lib.a"
    assert tgt.custom_commands == []

    # Valid: interface type (even though not in the standard list)
    # Type validation is lenient to allow emitter to handle unknown types gracefully
    tgt = builder.Target(
        artifact="iface",
        name="my_iface",
        alias="Project::MyIface",
        type="interface",
        sources=[],
        include_dirs=[],
        defines=[],
        compile_options=[],
        link_options=[],
        link_libs=[],
        deps=[],
    )
    assert tgt.type == "interface"

    # Invalid: empty artifact
    with pytest.raises(ValueError, match="artifact cannot be empty"):
        builder.Target(
            artifact="",
            name="name",
            alias=None,
            type="static",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=[],
        )

    # Invalid: empty name
    with pytest.raises(ValueError, match="name cannot be empty"):
        builder.Target(
            artifact="lib.a",
            name="",
            alias=None,
            type="static",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=[],
        )


def test_project_validation():
    # Valid project
    proj = builder.Project(
        name="myproject",
        version="1.0",
        namespace="MyProj",
        languages=["C"],
        targets=[],
        project_config=builder.ProjectGlobalConfig(
            vars={},
            flags={},
            defines=[],
            includes=[],
            feature_toggles={},
            sources=[],
        ),
    )
    assert proj.name == "myproject"

    # Invalid: empty name
    with pytest.raises(ValueError, match="name cannot be empty"):
        builder.Project(
            name="",
            version=None,
            namespace=None,
            languages=[],
            targets=[],
            project_config=builder.ProjectGlobalConfig(
                vars={},
                flags={},
                defines=[],
                includes=[],
                feature_toggles={},
                sources=[],
            ),
        )


def test_target_mapping_link_libs():
    """Test that target mappings with link_libs are applied to targets."""
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/app.c",
            output="app",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    from gmake2cmake.config import TargetMapping
    cfg = ConfigModel(
        project_name="Demo",
        target_mappings={
            "app": TargetMapping(
                src_name="app",
                dest_name="demo_app",
                link_libs=["m", "pthread"],
            )
        },
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    target = project.targets[0]
    assert "m" in target.link_libs
    assert "pthread" in target.link_libs
    assert target.link_libs == ["m", "pthread"]


def test_target_mapping_visibility():
    """Test that target mappings with visibility are applied to targets."""
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/lib.c",
            output="libcore.a",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    from gmake2cmake.config import TargetMapping
    cfg = ConfigModel(
        project_name="Demo",
        target_mappings={
            "libcore": TargetMapping(
                src_name="libcore",
                dest_name="demo_core",
                visibility="INTERFACE",
            )
        },
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    target = project.targets[0]
    assert target.visibility == "INTERFACE"


def test_target_mapping_link_libs_and_visibility():
    """Test that target mappings apply both link_libs and visibility together."""
    facts = evaluator.BuildFacts()
    facts.inferred_compiles.append(
        evaluator.InferredCompile(
            source="src/lib.c",
            output="libutil.a",
            language="c",
            flags=[],
            includes=[],
            defines=[],
            location=parser.SourceLocation("Makefile", 1, 1),
        )
    )
    from gmake2cmake.config import TargetMapping
    cfg = ConfigModel(
        project_name="Demo",
        target_mappings={
            "libutil": TargetMapping(
                src_name="libutil",
                dest_name="demo_util",
                link_libs=["z", "ssl"],
                visibility="PUBLIC",
            )
        },
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    target = project.targets[0]
    assert target.link_libs == ["ssl", "z"]  # sorted
    assert target.visibility == "PUBLIC"


def test_global_config_flag_mapping():
    """Test that flag mappings are applied to global config flags."""
    facts = evaluator.BuildFacts()
    facts.project_globals.flags["c"] = ["-O2", "-Wall"]
    facts.project_globals.flags["cpp"] = ["-O3"]

    cfg = ConfigModel(
        project_name="Demo",
        flag_mappings={"-O2": "-O3", "-Wall": "-Wextra"},
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    assert sorted(project.project_config.flags["c"]) == ["-O3", "-Wextra"]
    assert project.project_config.flags["cpp"] == ["-O3"]


def test_global_config_ignore_paths():
    """Test that ignored paths are removed from global config."""
    facts = evaluator.BuildFacts()
    facts.project_globals.includes = ["include", "temp/include", "build/include"]
    facts.project_globals.defines = ["MAIN_DEF", "TEMP_DEF"]
    facts.project_globals.sources = ["src/main.c", "temp/test.c"]

    cfg = ConfigModel(
        project_name="Demo",
        ignore_paths=["temp/*", "build/*"],
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    assert "include" in project.project_config.includes
    assert "temp/include" not in project.project_config.includes
    assert "build/include" not in project.project_config.includes
    assert "MAIN_DEF" in project.project_config.defines
    assert "TEMP_DEF" in project.project_config.defines
    assert "src/main.c" in project.project_config.sources
    assert "temp/test.c" not in project.project_config.sources


def test_global_config_normalize_paths():
    """Test that paths are normalized to posix format."""
    facts = evaluator.BuildFacts()
    facts.project_globals.includes = ["include\\core", "include/util"]

    cfg = ConfigModel(project_name="Demo")
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    assert "include/core" in project.project_config.includes
    assert "include/util" in project.project_config.includes
    assert "include\\core" not in project.project_config.includes


def test_global_config_unmapped_flags_diagnostic():
    """Test that unmapped global flags generate diagnostics."""
    facts = evaluator.BuildFacts()
    facts.project_globals.flags["c"] = ["-O2", "-Wunknown"]

    cfg = ConfigModel(
        project_name="Demo",
        flag_mappings={"-O2": "-O3"},
    )
    diagnostics = DiagnosticCollector()
    project = builder.build_project(facts, cfg, diagnostics).project
    assert project is not None
    assert any(d.code == "IR_UNMAPPED_FLAG" for d in diagnostics.diagnostics)
    unmapped_diag = next(d for d in diagnostics.diagnostics if d.code == "IR_UNMAPPED_FLAG")
    assert "-Wunknown" in unmapped_diag.message
