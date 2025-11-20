from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.fs import FileSystemAdapter
from gmake2cmake.ir.builder import Project, Target

GLOBAL_MODULE_NAME = "ProjectGlobalConfig.cmake"
PACKAGING_RULES_FILE = "Packaging.cmake"


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class EmitOptions:
    dry_run: bool
    packaging: bool
    namespace: str


def _usage_scope(target: Target) -> str:
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


def emit(project: Project, output_dir: Path, *, options: EmitOptions, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> List[GeneratedFile]:
    layout = plan_file_layout(project, output_dir)
    generated: List[GeneratedFile] = []
    alias_lookup = _build_alias_lookup(project.targets)
    has_global_module = bool(
        project.project_config.vars
        or project.project_config.flags
        or project.project_config.defines
        or project.project_config.includes
        or project.project_config.feature_toggles
    )
    has_global_interface = bool(project.project_config.includes or project.project_config.defines or project.project_config.flags)
    global_interface_alias: Optional[str] = None
    if has_global_module:
        global_interface_name, global_alias_name = _global_interface_names(options.namespace)
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
            except Exception as exc:  # pragma: no cover - IO error path
                add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {global_module_path}: {exc}")
    subdirs: List[str] = []
    for dirpath in sorted(layout, key=lambda p: Path(p).as_posix()):
        if dirpath == output_dir:
            continue
        try:
            rel = Path(dirpath).relative_to(output_dir).as_posix()
        except ValueError:
            rel = Path(dirpath).name
        subdirs.append(rel)
    subdirs = sorted(set(subdirs))
    root_content = render_root(
        project,
        subdirs,
        options=options,
        has_global_module=has_global_module,
        global_link=global_interface_alias,
        alias_lookup=alias_lookup,
        diagnostics=diagnostics,
    )
    root_path = output_dir / "CMakeLists.txt"
    generated.append(GeneratedFile(path=root_path.as_posix(), content=root_content))
    if not options.dry_run:
        try:
            fs.makedirs(root_path.parent)
            fs.write_text(root_path, root_content)
        except Exception as exc:  # pragma: no cover - IO error path
            add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {root_path}: {exc}")

    for dirpath, targets in layout.items():
        rel_dir = Path(dirpath)
        path = rel_dir / "CMakeLists.txt"
        if rel_dir == output_dir:
            continue
        content = "\n".join(
            render_target(
                target,
                rel_dir,
                options.namespace,
                alias_lookup=alias_lookup,
                global_link=global_interface_alias,
                diagnostics=diagnostics,
            )
            for target in targets
        )
        generated.append(GeneratedFile(path=path.as_posix(), content=content))
        if not options.dry_run:
            try:
                fs.makedirs(path.parent)
                fs.write_text(path, content)
            except Exception as exc:  # pragma: no cover
                add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {path}: {exc}")

    if options.packaging:
        pkg_files = render_packaging(project, options.namespace, has_global_module=has_global_module)
        for fname, content in pkg_files.items():
            full_path = output_dir / fname
            generated.append(GeneratedFile(path=full_path.as_posix(), content=content))
            if not options.dry_run:
                try:
                    fs.makedirs(full_path.parent)
                    fs.write_text(full_path, content)
                except Exception as exc:  # pragma: no cover
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
) -> str:
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
            lines.append(
                render_target(
                    target,
                    Path("."),
                    options.namespace,
                    alias_lookup=alias_lookup,
                    global_link=global_link,
                    diagnostics=diagnostics,
                )
            )
    if options.packaging:
        lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{PACKAGING_RULES_FILE}")')
    return "\n".join(lines) + "\n"


def render_global_module(project_config, namespace: str, *, interface_name: str, alias: str) -> str:
    lines = ["# Project global configuration"]
    for name, value in sorted(project_config.feature_toggles.items()):
        if isinstance(value, bool):
            default = "ON" if value else "OFF"
            lines.append(f'option({name} "Feature toggle from Make" {default})')
        else:
            lines.append(f'set({name} "{value}" CACHE STRING "Feature toggle from Make")')
    for name, value in sorted(project_config.vars.items()):
        lines.append(f"set({name} \"{value}\" CACHE STRING \"Global var from Make\")")
    for lang, flags in sorted(project_config.flags.items()):
        init_var = {"c": "C", "cpp": "CXX"}.get(lang, lang.upper())
        lines.append(f"set(CMAKE_{init_var}_FLAGS_INIT \"{' '.join(flags)}\")")
    needs_interface = bool(project_config.includes or project_config.defines or project_config.flags)
    if needs_interface:
        lines.append(f"add_library({interface_name} INTERFACE)")
        if project_config.includes:
            includes = " ".join(f'"{inc}"' for inc in sorted(set(project_config.includes)))
            lines.append(f"target_include_directories({interface_name} INTERFACE {includes})")
        if project_config.defines:
            defines = " ".join(sorted(set(project_config.defines)))
            lines.append(f"target_compile_definitions({interface_name} INTERFACE {defines})")
        compile_flags = sorted({flag for values in project_config.flags.values() for flag in values})
        if compile_flags:
            lines.append(f"target_compile_options({interface_name} INTERFACE {' '.join(compile_flags)})")
        lines.append(f"add_library({alias} ALIAS {interface_name})")
    return "\n".join(lines) + "\n"


def render_target(
    target: Target,
    rel_dir: Path,
    namespace: str,
    *,
    alias_lookup: Optional[Dict[str, str]] = None,
    global_link: Optional[str] = None,
    diagnostics: Optional[DiagnosticCollector] = None,
) -> str:
    lines: List[str] = []
    scope = _usage_scope(target)
    link_items: List[str] = []
    if global_link and target.type not in {"imported"}:
        link_items.append(global_link)
    link_items.extend(sorted(target.deps))
    link_items.extend(sorted(target.link_libs))
    if alias_lookup:
        link_items = [alias_lookup.get(item, item) for item in link_items]
    link_items = _dedupe(link_items)
    includes = sorted(set(target.include_dirs))
    defines = sorted(set(target.defines))
    compile_opts = sorted(set(target.compile_options))
    link_opts = sorted(set(target.link_options))

    def _emit_usage_requirements(name: str) -> None:
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

    if target.type in {"executable", "shared", "static", "object"}:
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
        lines.append(f"{cmake_fn}({target.name}{libtype})")
        if target.sources and target.type not in {"interface", "imported"}:
            srcs = " ".join(f'"{_relativize(s.path, rel_dir)}"' for s in target.sources)
            lines.append(f"target_sources({target.name} PRIVATE {srcs})")
        _emit_usage_requirements(target.name)
        if target.alias and target.type in {"shared", "static", "object"}:
            lines.append(f"add_library({target.alias} ALIAS {target.name})")
    elif target.type == "interface":
        lines.append(f"add_library({target.name} INTERFACE)")
        _emit_usage_requirements(target.name)
        if target.alias:
            lines.append(f"add_library({target.alias} ALIAS {target.name})")
    elif target.type == "imported":
        lines.append(f"add_library({target.name} UNKNOWN IMPORTED)")
        _emit_usage_requirements(target.name)
    else:
        if diagnostics is not None:
            add(diagnostics, "ERROR", "EMIT_UNKNOWN_TYPE", f"Unknown target type {target.type}")
        return "# Unknown target type\n"
    return "\n".join(lines) + "\n"


def render_packaging(project: Project, namespace: str, *, has_global_module: bool) -> Dict[str, str]:
    export_name = f"{project.name}Targets"
    config_name = f"{project.name}Config.cmake"
    version_name = f"{project.name}ConfigVersion.cmake"
    destination = f"lib/cmake/{project.name}"
    version_value = project.version or "0.1.0"
    installable = sorted({t.name for t in project.targets if t.type in {"shared", "static", "executable", "interface", "object"}})
    global_interface = None
    if has_global_module and (project.project_config.includes or project.project_config.defines or project.project_config.flags):
        global_interface, _ = _global_interface_names(namespace)
        installable = sorted(set(installable + [global_interface]))
    packaging_lines = [f"# Packaging for {project.name}"]
    if installable:
        packaging_lines.append(f"install(TARGETS {' '.join(installable)} EXPORT {export_name})")
    packaging_lines.append(
        f"install(EXPORT {export_name} NAMESPACE {namespace}:: DESTINATION {destination} FILE {project.name}Targets.cmake)"
    )
    packaging_lines.append(
        f"export(EXPORT {export_name} FILE \"${{CMAKE_CURRENT_BINARY_DIR}}/{project.name}Targets.cmake\" NAMESPACE {namespace}::)"
    )
    files_to_install = [config_name, version_name]
    if has_global_module:
        files_to_install.append(GLOBAL_MODULE_NAME)
    packaging_lines.append(
        "install(FILES "
        + " ".join(f"${{CMAKE_CURRENT_LIST_DIR}}/{fname}" for fname in files_to_install)
        + f" DESTINATION {destination})"
    )

    config_lines = [f"# Config for {project.name}"]
    if has_global_module:
        config_lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{GLOBAL_MODULE_NAME}")')
    config_lines.append(f'include("${{CMAKE_CURRENT_LIST_DIR}}/{project.name}Targets.cmake")')
    config_lines.append(f'set({project.name.upper()}_NAMESPACE "{namespace}::")')
    version_lines = [
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
    return {
        PACKAGING_RULES_FILE: "\n".join(packaging_lines) + "\n",
        config_name: "\n".join(config_lines) + "\n",
        version_name: "\n".join(version_lines) + "\n",
    }


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
            except Exception:
                dir_rel = Path(dir_rel.name)
        abs_dir = (output_dir / dir_rel).resolve()
        layout.setdefault(abs_dir, []).append(target)
    for dirpath, targets in layout.items():
        layout[dirpath] = sorted(targets, key=lambda t: t.name)
    return dict(sorted(layout.items(), key=lambda item: item[0].as_posix()))
