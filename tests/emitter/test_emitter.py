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
    visibility: str | None = None,
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
        visibility=visibility,
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
    emit_result = emitter.emit(
        project,
        tmp_path,
        options=emitter.EmitOptions(dry_run=True, packaging=False, namespace="Demo"),
        fs=_noop_fs(),
        diagnostics=diagnostics,
    )

    contents = {Path(g.path).relative_to(tmp_path).as_posix(): g.content for g in emit_result.generated_files}
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
    iface_result = emitter.render_target(iface, Path("."), "Demo", diagnostics=diagnostics)
    assert "add_library(demo_iface INTERFACE)" in iface_result.rendered
    assert 'target_include_directories(demo_iface INTERFACE "include")' in iface_result.rendered
    assert "target_compile_definitions(demo_iface INTERFACE IFACE_DEF)" in iface_result.rendered
    assert "target_link_options(demo_iface INTERFACE -pthread)" in iface_result.rendered
    assert "target_link_libraries(demo_iface INTERFACE m)" in iface_result.rendered
    assert "add_library(Demo::iface ALIAS demo_iface)" in iface_result.rendered

    imported_result = emitter.render_target(imported, Path("."), "Demo", diagnostics=diagnostics)
    assert "add_library(prebuilt UNKNOWN IMPORTED)" in imported_result.rendered
    assert "target_link_options(prebuilt INTERFACE -Wl,--as-needed)" in imported_result.rendered
    assert "target_link_libraries(prebuilt INTERFACE z)" in imported_result.rendered
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
    result = emitter.render_target(bad_target, Path("."), "Demo", diagnostics=diagnostics)
    assert "Unknown target type" in result.rendered
    assert any(d.code == "EMIT_UNKNOWN_TYPE" for d in diagnostics.diagnostics)
    assert result.unknown_constructs
    assert result.unknown_constructs[0].category == "toolchain_specific"


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

    emit_result = emitter.emit(
        project,
        tmp_path,
        options=emitter.EmitOptions(dry_run=False, packaging=False, namespace="Demo"),
        fs=FailingFS(),
        diagnostics=diagnostics,
    )

    assert any(d.code == "EMIT_WRITE_FAIL" for d in diagnostics.diagnostics)


def test_render_target_with_explicit_visibility():
    """Test that target's explicit visibility is used instead of type-based defaults."""
    # Target with INTERFACE visibility override
    target_iface = _make_target(
        artifact="libcore.a",
        name="demo_core",
        alias="Demo::core",
        target_type="static",
        visibility="INTERFACE",
        sources=[builder.SourceFile(path="src/core.c", language="c", flags=[])],
        include_dirs=["include"],
        link_libs=["m"],
    )
    result = emitter.render_target(target_iface, Path("."), "Demo")
    assert "target_include_directories(demo_core INTERFACE" in result.rendered
    assert "target_link_libraries(demo_core INTERFACE m)" in result.rendered

    # Target with PRIVATE visibility override
    target_private = _make_target(
        artifact="libutil.a",
        name="demo_util",
        target_type="static",
        visibility="PRIVATE",
        sources=[builder.SourceFile(path="src/util.c", language="c", flags=[])],
        include_dirs=["include/util"],
        link_libs=["z"],
    )
    result = emitter.render_target(target_private, Path("."), "Demo")
    assert "target_include_directories(demo_util PRIVATE" in result.rendered
    assert "target_link_libraries(demo_util PRIVATE z)" in result.rendered


def test_render_target_with_link_libs():
    """Test that link_libs from target mapping are included in rendered output."""
    target = _make_target(
        artifact="app",
        name="demo_app",
        target_type="executable",
        sources=[builder.SourceFile(path="main.c", language="c", flags=[])],
        link_libs=["m", "pthread"],
        deps=["demo_core"],
    )
    result = emitter.render_target(target, Path("."), "Demo")
    assert "target_link_libraries(demo_app PRIVATE demo_core m pthread)" in result.rendered


def test_render_target_default_visibility_unchanged():
    """Test that targets without explicit visibility use type-based defaults."""
    # Static library without visibility should use PUBLIC
    static_lib = _make_target(
        artifact="libcore.a",
        name="demo_core",
        target_type="static",
        sources=[builder.SourceFile(path="src/core.c", language="c", flags=[])],
        include_dirs=["include"],
    )
    result = emitter.render_target(static_lib, Path("."), "Demo")
    assert "target_include_directories(demo_core PUBLIC" in result.rendered

    # Executable without visibility should use PRIVATE
    exe = _make_target(
        artifact="app",
        name="demo_app",
        target_type="executable",
        sources=[builder.SourceFile(path="main.c", language="c", flags=[])],
        include_dirs=["include"],
    )
    result = emitter.render_target(exe, Path("."), "Demo")
    assert "target_include_directories(demo_app PRIVATE" in result.rendered

    # Interface without visibility should use INTERFACE
    iface = _make_target(
        artifact="iface",
        name="demo_iface",
        target_type="interface",
        include_dirs=["include"],
    )
    result = emitter.render_target(iface, Path("."), "Demo")
    assert "target_include_directories(demo_iface INTERFACE" in result.rendered


def test_emit_global_config_with_flag_mapping():
    """Test that flag mapping is reflected in emitted global module."""
    # Create global config with mapped flags
    project_config = builder.ProjectGlobalConfig(
        vars={},
        flags={"c": ["-O3", "-Wextra"]},  # these are already mapped
        defines=[],
        includes=[],
        feature_toggles={},
        sources=[],
    )
    target = _make_target(
        artifact="app",
        name="demo_app",
        target_type="executable",
    )
    project = builder.Project(
        name="Demo",
        version=None,
        namespace="Demo",
        languages=["C"],
        targets=[target],
        project_config=project_config,
    )
    rendered = emitter.render_global_module(
        project.project_config,
        "Demo",
        interface_name="demo_global_options",
        alias="Demo::GlobalOptions",
    )
    # Verify mapped flags appear in CMake
    assert 'set(CMAKE_C_FLAGS_INIT "-O3 -Wextra")' in rendered or \
           'set(CMAKE_C_FLAGS_INIT "-Wextra -O3")' in rendered


def test_render_target_with_custom_commands():
    """Test that custom commands are rendered in target output."""
    cc = builder.CustomCommand(
        name="build_gen",
        targets=["generated.h"],
        prerequisites=["template.txt"],
        commands=["generate --template template.txt --output generated.h"],
        outputs=["generated.h"],
        inputs=["template.txt"],
    )
    target = _make_target(
        artifact="app",
        name="demo_app",
        target_type="executable",
        sources=[builder.SourceFile(path="main.c", language="c", flags=[])],
    )
    target.custom_commands = [cc]
    result = emitter.render_target(target, Path("."), "Demo")
    assert "# Custom command for demo_app" in result.rendered
    assert "add_custom_command(OUTPUT" in result.rendered
    assert "generated.h" in result.rendered


def test_emit_with_custom_commands_dry_run(tmp_path):
    """Test that custom commands are preserved in dry-run mode."""
    cc = builder.CustomCommand(
        name="gen_code",
        targets=["code.c"],
        prerequisites=["spec.txt"],
        commands=["codegen spec.txt code.c"],
        outputs=["code.c"],
        inputs=["spec.txt"],
    )
    lib_target = _make_target(
        artifact="libcode.a",
        name="demo_code",
        target_type="static",
        sources=[builder.SourceFile(path="code.c", language="c", flags=[])],
    )
    lib_target.custom_commands = [cc]
    project = builder.Project(
        name="Demo",
        version="1.0.0",
        namespace="Demo",
        languages=["C"],
        targets=[lib_target],
        project_config=_project_config(),
    )
    diagnostics = DiagnosticCollector()
    emit_result = emitter.emit(
        project,
        tmp_path,
        options=emitter.EmitOptions(dry_run=True, packaging=False, namespace="Demo"),
        fs=_noop_fs(),
        diagnostics=diagnostics,
    )

    contents = {Path(g.path).relative_to(tmp_path).as_posix(): g.content for g in emit_result.generated_files}
    # Should have code.c subdir or generated at root
    lib_cmake_content = ""
    for path, content in contents.items():
        if "CMakeLists.txt" in path:
            lib_cmake_content = content
            break
    assert lib_cmake_content
    assert "add_custom_command" in lib_cmake_content or "# Custom command" in lib_cmake_content
