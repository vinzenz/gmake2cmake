from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.fs import FileSystemAdapter
from gmake2cmake.ir.builder import Project, Target


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class EmitOptions:
    dry_run: bool
    packaging: bool
    namespace: str


def emit(project: Project, output_dir: Path, *, options: EmitOptions, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> List[GeneratedFile]:
    layout = plan_file_layout(project, output_dir)
    generated: List[GeneratedFile] = []
    has_global_module = bool(project.project_config.vars or project.project_config.flags or project.project_config.includes)
    if has_global_module:
        global_module_path = output_dir / "ProjectGlobalConfig.cmake"
        global_content = render_global_module(project.project_config, options.namespace)
        generated.append(GeneratedFile(path=global_module_path.as_posix(), content=global_content))
        if not options.dry_run:
            try:
                fs.makedirs(global_module_path.parent)
                fs.write_text(global_module_path, global_content)
            except Exception as exc:  # pragma: no cover - IO error path
                add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {global_module_path}: {exc}")
    subdirs = []
    for dirpath in layout:
        if dirpath == output_dir:
            continue
        try:
            rel = Path(dirpath).relative_to(output_dir).as_posix()
        except ValueError:
            rel = Path(dirpath).name
        subdirs.append(rel)
    subdirs = sorted(set(subdirs))
    root_content = render_root(project, subdirs, options=options, has_global_module=has_global_module)
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
        content_lines: List[str] = []
        for target in targets:
            content_lines.append(render_target(target, rel_dir, options.namespace))
        content = "\n".join(content_lines)
        generated.append(GeneratedFile(path=path.as_posix(), content=content))
        if not options.dry_run:
            try:
                fs.makedirs(path.parent)
                fs.write_text(path, content)
            except Exception as exc:  # pragma: no cover
                add(diagnostics, "ERROR", "EMIT_WRITE_FAIL", f"Failed to write {path}: {exc}")

    if options.packaging:
        pkg_files = render_packaging(project, options.namespace)
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


def render_root(project: Project, subdirs: List[str], *, options: EmitOptions, has_global_module: bool) -> str:
    lines = [
        "cmake_minimum_required(VERSION 3.20)",
        f'project({project.name} LANGUAGES {" ".join(project.languages)})',
    ]
    if has_global_module:
        lines.append('include("${CMAKE_CURRENT_LIST_DIR}/ProjectGlobalConfig.cmake")')
    for sub in subdirs:
        lines.append(f'add_subdirectory("{sub}")')
    for target in project.targets:
        if target.sources and Path(target.sources[0].path).parent.as_posix() == ".":
            lines.append(render_target(target, Path("."), options.namespace))
    if options.packaging:
        lines.append("# Packaging enabled; install rules emitted in separate files")
    return "\n".join(lines) + "\n"


def render_global_module(project_config, namespace: str) -> str:
    lines = ["# Project global configuration"]
    for name, value in sorted(project_config.vars.items()):
        lines.append(f"set({name} \"{value}\" CACHE STRING \"Global var from Make\")")
    for inc in sorted(set(project_config.includes)):
        lines.append(f"include_directories(\"{inc}\")")
    for lang, flags in sorted(project_config.flags.items()):
        init_var = {"c": "CFLAGS", "cpp": "CXXFLAGS"}.get(lang, "CFLAGS")
        lines.append(f"set(CMAKE_{init_var}_INIT \"{' '.join(flags)}\")")
    return "\n".join(lines) + "\n"


def render_target(target: Target, rel_dir: Path, namespace: str) -> str:
    lines: List[str] = []
    if target.type in {"executable", "shared", "static"}:
        cmake_fn = {"executable": "add_executable", "shared": "add_library", "static": "add_library"}[target.type]
        libtype = "" if target.type == "executable" else " SHARED" if target.type == "shared" else " STATIC"
        lines.append(f"{cmake_fn}({target.name}{libtype})")
        if target.sources:
            srcs = " ".join(f'"{Path(s.path).relative_to(rel_dir).as_posix()}"' for s in target.sources)
            lines.append(f"target_sources({target.name} PRIVATE {srcs})")
        if target.compile_options:
            opts = " ".join(target.compile_options)
            lines.append(f"target_compile_options({target.name} PRIVATE {opts})")
        if target.alias:
            lines.append(f"add_library({namespace}::{Path(target.name).stem} ALIAS {target.name})")
    elif target.type == "object":
        lines.append(f"add_library({target.name} OBJECT)")
    else:
        add(None, "ERROR", "EMIT_UNKNOWN_TYPE", f"Unknown target type {target.type}")  # pragma: no cover
    return "\n".join(lines) + "\n"


def render_packaging(project: Project, namespace: str) -> Dict[str, str]:
    config_name = f"{project.name}Config.cmake"
    version_name = f"{project.name}ConfigVersion.cmake"
    return {
        config_name: f"# Config for {project.name}\ninclude(${{CMAKE_CURRENT_LIST_DIR}}/{project.name}Targets.cmake)\n",
        version_name: "set(PACKAGE_VERSION \"0.1.0\")\n",
    }


def plan_file_layout(project: Project, output_dir: Path) -> Dict[Path, List[Target]]:
    layout: Dict[Path, List[Target]] = {output_dir: []}
    for target in project.targets:
        dirs = [Path(s.path).parent for s in target.sources] if target.sources else [Path(".")]
        dir_rel = Path(".")
        if dirs:
            dir_rel = Path(min(dirs)).resolve()
        abs_dir = output_dir / dir_rel
        layout.setdefault(abs_dir, []).append(target)
    return layout
