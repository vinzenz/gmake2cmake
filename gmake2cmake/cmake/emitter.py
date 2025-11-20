from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.fs import FileSystemAdapter
from gmake2cmake.ir.builder import Project, Target
from gmake2cmake.ir.unknowns import UnknownConstruct, UnknownConstructFactory

GLOBAL_MODULE_NAME = "ProjectGlobalConfig.cmake"
PACKAGING_RULES_FILE = "Packaging.cmake"


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class EmitResult:
    generated_files: List[GeneratedFile]
    unknown_constructs: List[UnknownConstruct]


@dataclass
class RenderResult:
    rendered: str
    unknown_constructs: List[UnknownConstruct]


@dataclass
class EmitOptions:
    dry_run: bool
    packaging: bool
    namespace: str


def _usage_scope(target: Target) -> str:
    # Use target's explicit visibility if set, otherwise default based on type
    if target.visibility:
        return target.visibility
    if target.type in {"interface", "imported"}:
        return "INTERFACE"
    if target.type == "executable":
        return "PRIVATE"
    return "PUBLIC"


def _relativize(path: str, base: Path) -> str:
    candidate = Path(path)
    try:
        return candidate.relative_to(base).as_posix()
    except ValueError:
        return candidate.as_posix()


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _build_alias_lookup(targets: List[Target]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for tgt in targets:
        if not tgt.alias:
            continue
        lookup[tgt.alias] = tgt.alias
        lookup[tgt.name] = tgt.alias
        lookup[Path(tgt.artifact).stem] = tgt.alias
        lookup[Path(tgt.artifact).name] = tgt.alias
    return lookup


def _global_interface_names(namespace: str) -> Tuple[str, str]:
    physical = f"{namespace.lower()}_global_options"
    alias = f"{namespace}::GlobalOptions"
    return physical, alias


def emit(
    project: Project,
    output_dir: Path,
    *,
    options: EmitOptions,
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
    unknown_factory: Optional[UnknownConstructFactory] = None,
) -> EmitResult:
    unknown_factory = unknown_factory or UnknownConstructFactory()
    layout = plan_file_layout(project, output_dir)
    generated: List[GeneratedFile] = []
    unknown_constructs: List[UnknownConstruct] = []
    alias_lookup = _build_alias_lookup(project.targets)
    has_global_module = _has_global_module(project)
    global_interface_alias = _emit_global_module(
        project,
        output_dir,
        options,
        has_global_module,
        fs,
        diagnostics,
        alias_lookup,
        generated,
    )
    subdirs = _collect_subdirs(layout, output_dir)
    root_result = render_root(
        project,
        subdirs,
        options=options,
        has_global_module=has_global_module,
        global_link=global_interface_alias,
        alias_lookup=alias_lookup,
        diagnostics=diagnostics,
        unknown_factory=unknown_factory,
    )
    _record_root_file(output_dir, fs, diagnostics, generated, root_result, options.dry_run)
    unknown_constructs.extend(root_result.unknown_constructs)
    dir_results, nested_unknowns = _emit_directory_targets(
        layout,
        output_dir,
        options,
        alias_lookup,
        global_interface_alias,
        diagnostics,
        unknown_factory,
        fs,
    )
    generated.extend(dir_results)
    unknown_constructs.extend(nested_unknowns)
    if options.packaging:
        generated.extend(
            _emit_packaging_files(
                project, options.namespace, has_global_module, output_dir, fs, diagnostics, options.dry_run
            )
        )
    return EmitResult(generated_files=generated, unknown_constructs=unknown_constructs)


def _has_global_module(project: Project) -> bool:
    return bool(
        project.project_config.vars
        or project.project_config.flags
        or project.project_config.defines
        or project.project_config.includes
        or project.project_config.feature_toggles
    )


def _emit_global_module(
    project: Project,
    output_dir: Path,
    options: EmitOptions,
    has_global_module: bool,
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
    alias_lookup: Dict[str, str],
    generated: List[GeneratedFile],
) -> Optional[str]:
    has_global_interface = bool(project.project_config.includes or project.project_config.defines or project.project_config.flags)
    if not has_global_module:
        return None
    global_interface_name, global_alias_name = _global_interface_names(options.namespace)
    global_interface_alias: Optional[str] = None
    if has_global_interface:
        alias_lookup.setdefault(global_interface_name, global_alias_name)
        alias_lookup.setdefault(global_alias_name, global_alias_name)
        global_interface_alias = global_alias_name
    global_module_path = output_dir / GLOBAL_MODULE_NAME
    global_content = render_global_module(
        project.project_config,
        options.namespace,
        interface_name=global_interface_name,
        alias=global_alias_name,
    )
    generated.append(GeneratedFile(path=global_module_path.as_posix(), content=global_content))
    if not options.dry_run:
        try:
            fs.makedirs(global_module_path.parent)
            fs.write_text(global_module_path, global_content)
        except (OSError, PermissionError) as exc:  # pragma: no cover - IO error path
            add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {global_module_path}: {exc}")
    return global_interface_alias


def _collect_subdirs(layout: Dict[Path, List[Target]], output_dir: Path) -> List[str]:
    subdirs = []
    for dirpath in sorted(layout, key=lambda p: Path(p).as_posix()):
        if dirpath == output_dir:
            continue
        try:
            rel = Path(dirpath).relative_to(output_dir).as_posix()
        except ValueError:
            rel = Path(dirpath).name
        subdirs.append(rel)
    return sorted(set(subdirs))


def _record_root_file(
    output_dir: Path,
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
    generated: List[GeneratedFile],
    root_result: RenderResult,
    dry_run: bool,
) -> None:
    root_content = root_result.rendered
    root_path = output_dir / "CMakeLists.txt"
    generated.append(GeneratedFile(path=root_path.as_posix(), content=root_content))
    if dry_run:
        return
    try:
        fs.makedirs(root_path.parent)
        fs.write_text(root_path, root_content)
    except (OSError, PermissionError) as exc:  # pragma: no cover - IO error path
        add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {root_path}: {exc}")


def _emit_directory_targets(
    layout: Dict[Path, List[Target]],
    output_dir: Path,
    options: EmitOptions,
    alias_lookup: Dict[str, str],
    global_interface_alias: Optional[str],
    diagnostics: DiagnosticCollector,
    unknown_factory: UnknownConstructFactory,
    fs: FileSystemAdapter,
) -> Tuple[List[GeneratedFile], List[UnknownConstruct]]:
    generated: List[GeneratedFile] = []
    unknowns: List[UnknownConstruct] = []
    for dirpath, targets in layout.items():
        rel_dir = Path(dirpath)
        if rel_dir == output_dir:
            continue
        path = rel_dir / "CMakeLists.txt"
        rendered_targets = []
        for target in targets:
            result = render_target(
                target,
                rel_dir,
                options.namespace,
                alias_lookup=alias_lookup,
                global_link=global_interface_alias,
                diagnostics=diagnostics,
                unknown_factory=unknown_factory,
            )
            rendered_targets.append(result.rendered)
            unknowns.extend(result.unknown_constructs)
        content = "\n".join(rendered_targets)
        generated.append(GeneratedFile(path=path.as_posix(), content=content))
        if not options.dry_run:
            try:
                fs.makedirs(path.parent)
                fs.write_text(path, content)
            except (OSError, PermissionError) as exc:  # pragma: no cover
                add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {path}: {exc}")
    return generated, unknowns


def _emit_packaging_files(
    project: Project,
    namespace: str,
    has_global_module: bool,
    output_dir: Path,
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
    dry_run: bool,
) -> List[GeneratedFile]:
    generated: List[GeneratedFile] = []
    pkg_files = render_packaging(project, namespace, has_global_module=has_global_module)
    for fname, content in pkg_files.items():
        full_path = output_dir / fname
        generated.append(GeneratedFile(path=full_path.as_posix(), content=content))
        if dry_run:
            continue
        try:
            fs.makedirs(full_path.parent)
            fs.write_text(full_path, content)
        except (OSError, PermissionError) as exc:  # pragma: no cover
            add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {full_path}: {exc}")
    return generated


def render_root(
    project: Project,
    subdirs: List[str],
    *,
    options: EmitOptions,
    has_global_module: bool,
    global_link: Optional[str],
    alias_lookup: Dict[str, str],
    diagnostics: Optional[DiagnosticCollector] = None,
    unknown_factory: Optional[UnknownConstructFactory] = None,
) -> RenderResult:
    unknown_factory = unknown_factory or UnknownConstructFactory()
    unknown_constructs: List[UnknownConstruct] = []
    lines = [
        "cmake_minimum_required(VERSION 3.20)",
        f'project({project.name} LANGUAGES {" ".join(project.languages)})',
    ]
    if has_global_module:
        lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{GLOBAL_MODULE_NAME}")')
    for sub in subdirs:
        lines.append(f'add_subdirectory("{sub}")')
    for target in project.targets:
        if target.sources and Path(target.sources[0].path).parent.as_posix() == ".":
            result = render_target(
                target,
                Path("."),
                options.namespace,
                alias_lookup=alias_lookup,
                global_link=global_link,
                diagnostics=diagnostics,
                unknown_factory=unknown_factory,
            )
            lines.append(result.rendered)
            unknown_constructs.extend(result.unknown_constructs)
    if options.packaging:
        lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{PACKAGING_RULES_FILE}")')
    return RenderResult(rendered="\n".join(lines) + "\n", unknown_constructs=unknown_constructs)


def render_global_module(project_config, namespace: str, *, interface_name: str, alias: str) -> str:
    lines = ["# Project global configuration"]
    lines.extend(_render_feature_toggles(project_config))
    lines.extend(_render_global_vars(project_config))
    lines.extend(_render_flag_initializers(project_config))
    lines.extend(_render_global_interface(project_config, interface_name, alias))
    return "\n".join(lines) + "\n"


def _render_feature_toggles(project_config) -> List[str]:
    lines: List[str] = []
    for name, value in sorted(project_config.feature_toggles.items()):
        if isinstance(value, bool):
            default = "ON" if value else "OFF"
            lines.append(f'option({name} "Feature toggle from Make" {default})')
        else:
            lines.append(f'set({name} "{value}" CACHE STRING "Feature toggle from Make")')
    return lines


def _render_global_vars(project_config) -> List[str]:
    return [f"set({name} \"{value}\" CACHE STRING \"Global var from Make\")" for name, value in sorted(project_config.vars.items())]


def _render_flag_initializers(project_config) -> List[str]:
    lines: List[str] = []
    for lang, flags in sorted(project_config.flags.items()):
        init_var = {"c": "C", "cpp": "CXX"}.get(lang, lang.upper())
        lines.append(f"set(CMAKE_{init_var}_FLAGS_INIT \"{' '.join(flags)}\")")
    return lines


def _render_global_interface(project_config, interface_name: str, alias: str) -> List[str]:
    needs_interface = bool(project_config.includes or project_config.defines or project_config.flags)
    if not needs_interface:
        return []
    lines: List[str] = [f"add_library({interface_name} INTERFACE)"]
    include_line = _format_interface_includes(project_config.includes, interface_name)
    if include_line:
        lines.append(include_line)
    defines_line = _format_interface_defines(project_config.defines, interface_name)
    if defines_line:
        lines.append(defines_line)
    flags_line = _format_interface_flags(project_config.flags, interface_name)
    if flags_line:
        lines.append(flags_line)
    lines.append(f"add_library({alias} ALIAS {interface_name})")
    return lines


def _format_interface_includes(includes: List[str], interface_name: str) -> Optional[str]:
    if not includes:
        return None
    formatted = " ".join(f'"{inc}"' for inc in sorted(set(includes)))
    return f"target_include_directories({interface_name} INTERFACE {formatted})"


def _format_interface_defines(defines: List[str], interface_name: str) -> Optional[str]:
    if not defines:
        return None
    formatted = " ".join(sorted(set(defines)))
    return f"target_compile_definitions({interface_name} INTERFACE {formatted})"


def _format_interface_flags(flags: Dict[str, List[str]], interface_name: str) -> Optional[str]:
    compile_flags = sorted({flag for values in flags.values() for flag in values})
    if not compile_flags:
        return None
    return f"target_compile_options({interface_name} INTERFACE {' '.join(compile_flags)})"


def render_target(
    target: Target,
    rel_dir: Path,
    namespace: str,
    *,
    alias_lookup: Optional[Dict[str, str]] = None,
    global_link: Optional[str] = None,
    diagnostics: Optional[DiagnosticCollector] = None,
    unknown_factory: Optional[UnknownConstructFactory] = None,
) -> RenderResult:
    unknown_factory = unknown_factory or UnknownConstructFactory()
    unknown_constructs: List[UnknownConstruct] = []
    lines: List[str] = []
    scope = _usage_scope(target)
    link_items = _build_link_items(target, global_link, alias_lookup)
    includes = sorted(set(target.include_dirs))
    defines = sorted(set(target.defines))
    compile_opts = sorted(set(target.compile_options))
    link_opts = sorted(set(target.link_options))

    renderers = {
        "executable": _render_binary_target,
        "shared": _render_binary_target,
        "static": _render_binary_target,
        "object": _render_binary_target,
        "interface": _render_interface_target,
        "imported": _render_imported_target,
    }

    renderer = renderers.get(target.type)
    if renderer is None:
        return _handle_unknown_target_type(target, rel_dir, diagnostics, unknown_factory, unknown_constructs)

    lines.extend(
        renderer(
            target,
            rel_dir,
            scope,
            includes,
            defines,
            compile_opts,
            link_opts,
            link_items,
        )
    )
    lines.extend(_render_custom_commands(target, rel_dir))
    return RenderResult(rendered="\n".join(lines) + "\n", unknown_constructs=unknown_constructs)


def _build_link_items(
    target: Target, global_link: Optional[str], alias_lookup: Optional[Dict[str, str]]
) -> List[str]:
    link_items: List[str] = []
    if global_link and target.type not in {"imported"}:
        link_items.append(global_link)
    link_items.extend(sorted(target.deps))
    link_items.extend(sorted(target.link_libs))
    if alias_lookup:
        link_items = [alias_lookup.get(item, item) for item in link_items]
    return _dedupe(link_items)


def _render_custom_commands(target: Target, rel_dir: Path) -> List[str]:
    lines: List[str] = []
    for cc in target.custom_commands:
        lines.append(f"# Custom command for {target.name}")
        if not cc.commands:
            continue
        outputs_str = " ".join(f'"{_relativize(o, rel_dir)}"' for o in cc.outputs) if cc.outputs else target.name
        inputs_str = " ".join(f'"{_relativize(i, rel_dir)}"' for i in cc.inputs) if cc.inputs else ""
        command_str = " && ".join(cc.commands)
        lines.append(f'add_custom_command(OUTPUT {outputs_str}')
        if inputs_str:
            lines.append(f'  DEPENDS {inputs_str}')
        lines.append(f'  COMMAND {command_str})')
    return lines


def _render_unknown(unknown_constructs: List[UnknownConstruct], uc: UnknownConstruct) -> RenderResult:
    unknown_constructs.append(uc)
    return RenderResult(rendered="# Unknown target type\n", unknown_constructs=unknown_constructs)


def _usage_requirements(
    name: str,
    scope: str,
    includes: List[str],
    defines: List[str],
    compile_opts: List[str],
    link_opts: List[str],
    link_items: List[str],
    rel_dir: Path,
) -> List[str]:
    lines: List[str] = []
    if includes:
        parts = " ".join(f'"{_relativize(inc, rel_dir)}"' for inc in includes)
        lines.append(f"target_include_directories({name} {scope} {parts})")
    if defines:
        lines.append(f"target_compile_definitions({name} {scope} {' '.join(defines)})")
    if compile_opts:
        lines.append(f"target_compile_options({name} {scope} {' '.join(compile_opts)})")
    if link_opts:
        lines.append(f"target_link_options({name} {scope} {' '.join(link_opts)})")
    if link_items:
        lines.append(f"target_link_libraries({name} {scope} {' '.join(link_items)})")
    return lines


def _render_binary_target(
    target: Target,
    rel_dir: Path,
    scope: str,
    includes: List[str],
    defines: List[str],
    compile_opts: List[str],
    link_opts: List[str],
    link_items: List[str],
) -> List[str]:
    cmake_fn = {"executable": "add_executable", "shared": "add_library", "static": "add_library", "object": "add_library"}[
        target.type
    ]
    libtype = ""
    if target.type == "shared":
        libtype = " SHARED"
    elif target.type == "static":
        libtype = " STATIC"
    elif target.type == "object":
        libtype = " OBJECT"
    lines = [f"{cmake_fn}({target.name}{libtype})"]
    if target.sources and target.type not in {"interface", "imported"}:
        srcs = " ".join(f'"{_relativize(s.path, rel_dir)}"' for s in target.sources)
        lines.append(f"target_sources({target.name} PRIVATE {srcs})")
    lines.extend(_usage_requirements(target.name, scope, includes, defines, compile_opts, link_opts, link_items, rel_dir))
    if target.alias and target.type in {"shared", "static", "object"}:
        lines.append(f"add_library({target.alias} ALIAS {target.name})")
    return lines


def _render_interface_target(
    target: Target,
    rel_dir: Path,
    scope: str,
    includes: List[str],
    defines: List[str],
    compile_opts: List[str],
    link_opts: List[str],
    link_items: List[str],
) -> List[str]:
    lines = [f"add_library({target.name} INTERFACE)"]
    lines.extend(_usage_requirements(target.name, scope, includes, defines, compile_opts, link_opts, link_items, rel_dir))
    if target.alias:
        lines.append(f"add_library({target.alias} ALIAS {target.name})")
    return lines


def _render_imported_target(
    target: Target,
    rel_dir: Path,
    scope: str,
    includes: List[str],
    defines: List[str],
    compile_opts: List[str],
    link_opts: List[str],
    link_items: List[str],
) -> List[str]:
    lines = [f"add_library({target.name} UNKNOWN IMPORTED)"]
    lines.extend(_usage_requirements(target.name, scope, includes, defines, compile_opts, link_opts, link_items, rel_dir))
    return lines


def _handle_unknown_target_type(
    target: Target,
    rel_dir: Path,
    diagnostics: Optional[DiagnosticCollector],
    unknown_factory: UnknownConstructFactory,
    unknown_constructs: List[UnknownConstruct],
) -> RenderResult:
    if diagnostics is not None:
        add(diagnostics, "ERROR", "EMIT_UNKNOWN_TYPE", f"Unknown target type {target.type}")
    uc = unknown_factory.create(
        category="toolchain_specific",
        file=rel_dir.as_posix(),
        raw_snippet=target.type,
        normalized_form=f"unknown_target_type:{target.type}",
        context={"targets": [target.name]},
        impact={"result": "target_not_generated"},
        cmake_status="not_generated",
        suggested_action="manual_review",
    )
    return _render_unknown(unknown_constructs, uc)


def render_packaging(project: Project, namespace: str, *, has_global_module: bool) -> Dict[str, str]:
    export_name = f"{project.name}Targets"
    config_name = f"{project.name}Config.cmake"
    version_name = f"{project.name}ConfigVersion.cmake"
    destination = f"lib/cmake/{project.name}"
    version_value = project.version or "0.1.0"

    installable = _collect_installable_targets(project, namespace, has_global_module)
    packaging_lines = _render_packaging_rules(project, installable, export_name, destination, config_name, version_name, has_global_module)
    config_lines = _render_config_lines(project, namespace, has_global_module)
    version_lines = _render_version_lines(version_value)

    return {
        PACKAGING_RULES_FILE: "\n".join(packaging_lines) + "\n",
        config_name: "\n".join(config_lines) + "\n",
        version_name: "\n".join(version_lines) + "\n",
    }


def _collect_installable_targets(project: Project, namespace: str, has_global_module: bool) -> List[str]:
    installable = sorted({t.name for t in project.targets if t.type in {"shared", "static", "executable", "interface", "object"}})
    if has_global_module and (project.project_config.includes or project.project_config.defines or project.project_config.flags):
        global_interface, _ = _global_interface_names(namespace)
        installable = sorted(set(installable + [global_interface]))
    return installable


def _render_packaging_rules(
    project: Project,
    installable: List[str],
    export_name: str,
    destination: str,
    config_name: str,
    version_name: str,
    has_global_module: bool,
) -> List[str]:
    packaging_lines = [f"# Packaging for {project.name}"]
    if installable:
        packaging_lines.append(f"install(TARGETS {' '.join(installable)} EXPORT {export_name})")
    packaging_lines.append(
        f"install(EXPORT {export_name} NAMESPACE {project.namespace}:: DESTINATION {destination} FILE {project.name}Targets.cmake)"
    )
    packaging_lines.append(
        f"export(EXPORT {export_name} FILE \"${{CMAKE_CURRENT_BINARY_DIR}}/{project.name}Targets.cmake\" NAMESPACE {project.namespace}::)"
    )
    files_to_install = [config_name, version_name]
    if has_global_module:
        files_to_install.append(GLOBAL_MODULE_NAME)
    packaging_lines.append(
        "install(FILES "
        + " ".join(f"${{CMAKE_CURRENT_LIST_DIR}}/{fname}" for fname in files_to_install)
        + f" DESTINATION {destination})"
    )
    return packaging_lines


def _render_config_lines(project: Project, namespace: str, has_global_module: bool) -> List[str]:
    config_lines = [f"# Config for {project.name}"]
    if has_global_module:
        config_lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{GLOBAL_MODULE_NAME}")')
    config_lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{project.name}Targets.cmake")')
    config_lines.append(f'set({project.name.upper()}_NAMESPACE "{namespace}::")')
    return config_lines


def _render_version_lines(version_value: str) -> List[str]:
    return [
        f'set(PACKAGE_VERSION "{version_value}")',
        "if(PACKAGE_FIND_VERSION)",
        "  if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)",
        "    set(PACKAGE_VERSION_COMPATIBLE FALSE)",
        "  else()",
        "    set(PACKAGE_VERSION_COMPATIBLE TRUE)",
        "    if(PACKAGE_FIND_VERSION STREQUAL PACKAGE_VERSION)",
        "      set(PACKAGE_VERSION_EXACT TRUE)",
        "    endif()",
        "  endif()",
        "endif()",
    ]


def plan_file_layout(project: Project, output_dir: Path) -> Dict[Path, List[Target]]:
    layout: Dict[Path, List[Target]] = {output_dir: []}
    for target in project.targets:
        dirs = [Path(s.path).parent for s in target.sources] if target.sources else [Path(".")]
        dir_rel = Path(".")
        if dirs:
            dir_rel = min((Path(d) for d in dirs), key=lambda p: p.as_posix())
        if dir_rel.is_absolute():
            try:
                dir_rel = dir_rel.relative_to(Path(".").resolve())
            except ValueError:
                dir_rel = Path(dir_rel.name)
        abs_dir = (output_dir / dir_rel).resolve()
        layout.setdefault(abs_dir, []).append(target)
    for dirpath, targets in layout.items():
        layout[dirpath] = sorted(targets, key=lambda t: t.name)
    return dict(sorted(layout.items(), key=lambda item: item[0].as_posix()))
