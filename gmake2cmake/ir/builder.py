from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from gmake2cmake.config import ConfigModel, apply_flag_mapping, classify_library_override
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.make.evaluator import BuildFacts, InferredCompile, EvaluatedRule, ProjectGlobals


@dataclass
class SourceFile:
    path: str
    language: str
    flags: List[str]


@dataclass
class Target:
    name: str
    alias: Optional[str]
    type: str
    sources: List[SourceFile]
    include_dirs: List[str]
    defines: List[str]
    compile_options: List[str]
    link_options: List[str]
    link_libs: List[str]
    deps: List[str]
    custom_commands: List = None


@dataclass
class ProjectGlobalConfig:
    vars: Dict[str, str]
    flags: Dict[str, List[str]]
    defines: List[str]
    includes: List[str]
    feature_toggles: Dict[str, str | bool]
    sources: List[str]


@dataclass
class Project:
    name: str
    version: Optional[str]
    namespace: Optional[str]
    languages: List[str]
    targets: List[Target]
    project_config: ProjectGlobalConfig


@dataclass
class IRBuildResult:
    project: Optional[Project]
    diagnostics: List


def build_project(facts: BuildFacts, config: ConfigModel, diagnostics: DiagnosticCollector) -> IRBuildResult:
    name = config.project_name or "project"
    namespace = config.namespace or name
    languages = sorted({c.language for c in facts.inferred_compiles} or {"C"})
    project_config = build_project_global_config(facts.project_globals, config, diagnostics)
    targets = build_targets(facts, config, diagnostics, namespace)
    project = Project(name=name, version=config.version, namespace=namespace, languages=languages, targets=targets, project_config=project_config)
    validate_ir(project, diagnostics)
    return IRBuildResult(project=project, diagnostics=diagnostics.diagnostics)


def build_project_global_config(globals: ProjectGlobals, config: ConfigModel, diagnostics: DiagnosticCollector) -> ProjectGlobalConfig:
    return ProjectGlobalConfig(
        vars=dict(globals.vars),
        flags=dict(globals.flags),
        defines=list(globals.defines),
        includes=list(globals.includes),
        feature_toggles=dict(globals.feature_toggles),
        sources=list(globals.sources),
    )


def build_targets(facts: BuildFacts, config: ConfigModel, diagnostics: DiagnosticCollector, namespace: str) -> List[Target]:
    grouped: Dict[str, List[InferredCompile]] = {}
    for comp in facts.inferred_compiles:
        key = comp.output or comp.source
        grouped.setdefault(key, []).append(comp)
    targets: List[Target] = []
    for artifact, compiles in grouped.items():
        ttype = _infer_type(artifact)
        physical_name = _physical_name(namespace, artifact)
        alias_name = f"{namespace}::{Path(artifact).stem}"
        sources = make_source_files(compiles)
        compile_flags = []
        unmapped_flags = []
        for c in compiles:
            mapped, unmapped = apply_flag_mapping(c.flags, config)
            compile_flags.extend(mapped)
            unmapped_flags.extend(unmapped)
        if unmapped_flags:
            add(diagnostics, "WARN", "IR_UNMAPPED_FLAG", f"Unmapped flags: {','.join(sorted(set(unmapped_flags)))}")
        target_mapping = config.target_mappings.get(Path(artifact).stem)
        if target_mapping:
            physical_name = target_mapping.dest_name
            if target_mapping.type_override:
                ttype = target_mapping.type_override
        targets.append(
            Target(
                name=physical_name,
                alias=alias_name,
                type=ttype,
                sources=sources,
                include_dirs=[],
                defines=[],
                compile_options=sorted(set(compile_flags)),
                link_options=[],
                link_libs=[],
                deps=[],
                custom_commands=[],
            )
        )
    attach_dependencies(targets, facts.rules)
    targets = sorted(targets, key=lambda t: t.name)
    return targets


def _infer_type(artifact: str) -> str:
    if artifact.endswith(".a"):
        return "static"
    if artifact.endswith((".so", ".dylib")):
        return "shared"
    if artifact.endswith(".o"):
        return "object"
    return "executable"


def _physical_name(namespace: str, artifact: str) -> str:
    stem = Path(artifact).stem
    return f"{namespace.lower()}_{stem}"


def make_source_files(compiles: List[InferredCompile]) -> List[SourceFile]:
    seen = {}
    for comp in compiles:
        path = comp.source.replace("\\", "/")
        if path in seen:
            seen[path].flags = sorted(set(seen[path].flags + comp.flags))
        else:
            seen[path] = SourceFile(path=path, language=comp.language, flags=comp.flags)
    return sorted(seen.values(), key=lambda s: s.path)


def attach_dependencies(targets: List[Target], rules: List[EvaluatedRule]) -> None:
    target_names = {t.name: t for t in targets}
    for rule in rules:
        for prereq in rule.prerequisites:
            stem = Path(prereq).stem
            for t in targets:
                if Path(t.name).stem == stem and t.name in target_names:
                    continue
        # simplified: not attaching specific deps beyond grouping by artifact here


def validate_ir(project: Project, diagnostics: DiagnosticCollector) -> None:
    names = set()
    aliases = set()
    for t in project.targets:
        if t.name in names:
            add(diagnostics, "ERROR", "IR_DUP_TARGET", f"Duplicate target {t.name}")
        names.add(t.name)
        if t.alias:
            if t.alias in aliases:
                add(diagnostics, "ERROR", "IR_DUP_ALIAS", f"Duplicate alias {t.alias}")
            aliases.add(t.alias)
