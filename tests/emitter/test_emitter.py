from __future__ import annotations

from pathlib import Path

from gmake2cmake.cmake import emitter
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir import builder


def _noop_fs():
    class _FS:
        def makedirs(self, path):  # pragma: no cover - dry-run avoids fs usage
            return None

        def write_text(self, path, data):  # pragma: no cover - dry-run avoids fs usage
            raise AssertionError("write_text should not be called in dry-run mode")

        def exists(self, path):  # pragma: no cover - unused
            return False

        def is_file(self, path):  # pragma: no cover - unused
            return False

    return _FS()


def _make_target(
    *,
    artifact: str,
    name: str,
    target_type: str,
    alias: str | None = None,
    sources: list[builder.SourceFile] | None = None,
    include_dirs: list[str] | None = None,
    defines: list[str] | None = None,
    compile_options: list[str] | None = None,
    link_options: list[str] | None = None,
    link_libs: list[str] | None = None,
    deps: list[str] | None = None,
) -> builder.Target:
    return builder.Target(
        artifact=artifact,
        name=name,
        alias=alias,
        type=target_type,
        sources=sources or [],
        include_dirs=include_dirs or [],
        defines=defines or [],
        compile_options=compile_options or [],
        link_options=link_options or [],
        link_libs=link_libs or [],
        deps=deps or [],
        custom_commands=[],
    )


def _project_config(**overrides):
    base = dict(
        vars={},
        flags={},
        defines=[],
        includes=[],
        feature_toggles={},
        sources=[],
    )
    base.update(overrides)
    return builder.ProjectGlobalConfig(**base)


def test_emit_alias_and_global_options_module(tmp_path):
    project_config = _project_config(
        vars={"OPT": "1"},
        flags={"c": ["-O2"]},
        defines=["USE_DEMO"],
        includes=["include"],
        feature_toggles={"WITH_SSL": True},
    )
    lib_target = _make_target(
        artifact="libcore.a",
        name="demo_core",
        alias="Demo::core",
        target_type="static",
        sources=[builder.SourceFile(path="src/core.c", language="c", flags=[])],
        include_dirs=["include/core"],
        defines=["CORE_DEF"],
        compile_options=["-Wall"],
    )
    exe_target = _make_target(
        artifact="app",
        name="demo_app",
        target_type="executable",
        sources=[builder.SourceFile(path="app/main.c", language="c", flags=[])],
        deps=["demo_core"],
    )
    project = builder.Project(
        name="Demo",
        version="1.0.0",
        namespace="Demo",
        languages=["C"],
        targets=[lib_target, exe_target],
        project_config=project_config,
    )
    diagnostics = DiagnosticCollector()
    generated = emitter.emit(
        project,
        tmp_path,
        options=emitter.EmitOptions(dry_run=True, packaging=False, namespace="Demo"),
        fs=_noop_fs(),
        diagnostics=diagnostics,
    )

    contents = {Path(g.path).relative_to(tmp_path).as_posix(): g.content for g in generated}
    global_module = contents["ProjectGlobalConfig.cmake"]
    assert "add_library(demo_global_options INTERFACE)" in global_module
    assert "add_library(Demo::GlobalOptions ALIAS demo_global_options)" in global_module
    assert 'target_include_directories(demo_global_options INTERFACE "include")' in global_module
    assert not any(line.startswith("include_directories") for line in global_module.splitlines())

    lib_cmake = contents["src/CMakeLists.txt"]
    assert "add_library(demo_core STATIC)" in lib_cmake
    assert "add_library(Demo::core ALIAS demo_core)" in lib_cmake
    assert "target_link_libraries(demo_core PUBLIC Demo::GlobalOptions)" in lib_cmake

    exe_cmake = contents["app/CMakeLists.txt"]
    assert "target_link_libraries(demo_app PRIVATE Demo::GlobalOptions Demo::core)" in exe_cmake
    assert not diagnostics.diagnostics


def test_render_target_interface_and_imported_targets():
    iface = _make_target(
        artifact="iface",
        name="demo_iface",
        alias="Demo::iface",
        target_type="interface",
        include_dirs=["include"],
        defines=["IFACE_DEF"],
        compile_options=["-fPIC"],
        link_options=["-pthread"],
        link_libs=["m"],
    )
    imported = _make_target(
        artifact="prebuilt",
        name="prebuilt",
        target_type="imported",
        link_options=["-Wl,--as-needed"],
        link_libs=["z"],
    )
    diagnostics = DiagnosticCollector()
    iface_rendered = emitter.render_target(iface, Path("."), "Demo", diagnostics=diagnostics)
    assert "add_library(demo_iface INTERFACE)" in iface_rendered
    assert 'target_include_directories(demo_iface INTERFACE "include")' in iface_rendered
    assert "target_compile_definitions(demo_iface INTERFACE IFACE_DEF)" in iface_rendered
    assert "target_link_options(demo_iface INTERFACE -pthread)" in iface_rendered
    assert "target_link_libraries(demo_iface INTERFACE m)" in iface_rendered
    assert "add_library(Demo::iface ALIAS demo_iface)" in iface_rendered

    imported_rendered = emitter.render_target(imported, Path("."), "Demo", diagnostics=diagnostics)
    assert "add_library(prebuilt UNKNOWN IMPORTED)" in imported_rendered
    assert "target_link_options(prebuilt INTERFACE -Wl,--as-needed)" in imported_rendered
    assert "target_link_libraries(prebuilt INTERFACE z)" in imported_rendered
    assert not diagnostics.diagnostics


def test_render_packaging_outputs_namespace_consistency():
    project_config = _project_config(includes=["config"], defines=["PKG_DEF"])
    target = _make_target(
        artifact="libdemo.a",
        name="demo_lib",
        alias="DemoNS::demo",
        target_type="static",
    )
    project = builder.Project(
        name="Demo",
        version="2.5.0",
        namespace="DemoNS",
        languages=["C"],
        targets=[target],
        project_config=project_config,
    )
    pkg_files = emitter.render_packaging(project, "DemoNS", has_global_module=True)
    packaging_rules = pkg_files[emitter.PACKAGING_RULES_FILE]
    assert "NAMESPACE DemoNS::" in packaging_rules
    assert "install(TARGETS demo_lib" in packaging_rules
    assert "ProjectGlobalConfig.cmake" in packaging_rules

    config_content = pkg_files["DemoConfig.cmake"]
    assert 'include("${CMAKE_CURRENT_LIST_DIR}/ProjectGlobalConfig.cmake")' in config_content
    assert 'include("${CMAKE_CURRENT_LIST_DIR}/DemoTargets.cmake")' in config_content
    assert 'set(DEMO_NAMESPACE "DemoNS::")' in config_content

    version_content = pkg_files["DemoConfigVersion.cmake"]
    assert 'set(PACKAGE_VERSION "2.5.0")' in version_content


def test_render_target_unknown_type_diagnostic():
    diagnostics = DiagnosticCollector()
    bad_target = _make_target(
        artifact="unknown",
        name="weird",
        target_type="custom",
        sources=[builder.SourceFile(path="file.c", language="c", flags=[])],
    )
    rendered = emitter.render_target(bad_target, Path("."), "Demo", diagnostics=diagnostics)
    assert "Unknown target type" in rendered
    assert any(d.code == "EMIT_UNKNOWN_TYPE" for d in diagnostics.diagnostics)


def test_emit_reports_write_failures(tmp_path):
    simple_target = _make_target(
        artifact="main",
        name="demo_app",
        target_type="executable",
        sources=[builder.SourceFile(path="main.c", language="c", flags=[])],
    )
    project = builder.Project(
        name="Demo",
        version=None,
        namespace="Demo",
        languages=["C"],
        targets=[simple_target],
        project_config=_project_config(),
    )
    diagnostics = DiagnosticCollector()

    class FailingFS:
        def makedirs(self, path):
            return None

        def write_text(self, path, data):
            raise IOError("nope")

        def exists(self, path):
            return False

        def is_file(self, path):
            return False

    emitter.emit(
        project,
        tmp_path,
        options=emitter.EmitOptions(dry_run=False, packaging=False, namespace="Demo"),
        fs=FailingFS(),
        diagnostics=diagnostics,
    )

    assert any(d.code == "EMIT_WRITE_FAIL" for d in diagnostics.diagnostics)
