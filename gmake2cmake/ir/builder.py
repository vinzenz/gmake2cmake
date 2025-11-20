from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from gmake2cmake.config import (
    ConfigModel,
    apply_flag_mapping,
    classify_library_override,
    should_ignore_path,
)
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.unknowns import UnknownConstruct
from gmake2cmake.make.evaluator import BuildFacts, EvaluatedRule, InferredCompile, ProjectGlobals


@dataclass
class CustomCommand:
    """Represents a custom make command to be rendered as CMake custom command/target."""
    name: str
    targets: List[str]
    prerequisites: List[str]
    commands: List[str]
    working_dir: Optional[str] = None
    outputs: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)


@dataclass
class SourceFile:
    path: str
    language: str
    flags: List[str]

    def __post_init__(self) -> None:
        if not self.path or not self.path.strip():
            raise ValueError("path cannot be empty")
        if not self.language or not self.language.strip():
            raise ValueError("language cannot be empty")


@dataclass
class Target:
    artifact: str
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
    custom_commands: List[CustomCommand] = field(default_factory=list)
    visibility: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact or not self.artifact.strip():
            raise ValueError("artifact cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        # Note: type is not strictly validated here to allow emitter to handle unknown types gracefully


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
    unknown_constructs: List[UnknownConstruct] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")


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
    project = Project(
        name=name,
        version=config.version,
        namespace=namespace,
        languages=languages,
        targets=targets,
        project_config=project_config,
        unknown_constructs=list(facts.unknown_constructs),
    )
    validate_ir(project, diagnostics)
    return IRBuildResult(project=project, diagnostics=diagnostics.diagnostics)


def build_project_global_config(globals: ProjectGlobals, config: ConfigModel, diagnostics: DiagnosticCollector) -> ProjectGlobalConfig:
    # Normalize paths to posix and filter ignored paths
    def normalize_and_filter(items: List[str]) -> List[str]:
        result = []
        seen = set()
        for item in items:
            # Normalize path separators to posix
            norm_item = item.replace("\\", "/")
            # Skip if ignored and not already seen
            if should_ignore_path(norm_item, config):
                continue
            if norm_item not in seen:
                result.append(norm_item)
                seen.add(norm_item)
        return result

    # Apply flag mappings and collect diagnostics
    def apply_flag_mappings_to_lang_flags(flags_by_lang: Dict[str, List[str]]) -> Dict[str, List[str]]:
        result = {}
        all_unmapped = set()
        for lang, flag_list in flags_by_lang.items():
            mapped, unmapped = apply_flag_mapping(flag_list, config)
            result[lang] = mapped
            all_unmapped.update(unmapped)

        # Report unmapped flags if any
        if all_unmapped:
            add(diagnostics, "WARN", "IR_UNMAPPED_FLAG", f"Unmapped global flags: {','.join(sorted(all_unmapped))}")

        return result

    return ProjectGlobalConfig(
        vars=dict(globals.vars),
        flags=apply_flag_mappings_to_lang_flags(globals.flags),
        defines=sorted(set(normalize_and_filter(globals.defines))),
        includes=sorted(set(normalize_and_filter(globals.includes))),
        feature_toggles=dict(globals.feature_toggles),
        sources=sorted(set(normalize_and_filter(globals.sources))),
    )


def build_targets(facts: BuildFacts, config: ConfigModel, diagnostics: DiagnosticCollector, namespace: str) -> List[Target]:
    grouped: Dict[str, List[InferredCompile]] = {}
    for comp in facts.inferred_compiles:
        key = comp.output or comp.source
        grouped.setdefault(key, []).append(comp)
    artifact_map: Dict[str, Target] = {}
    targets: List[Target] = []
    for artifact, compiles in grouped.items():
        ttype = _infer_type(artifact)
        physical_name = _physical_name(namespace, artifact)
        alias_name = f"{namespace}::{Path(artifact).stem}"
        override = classify_library_override(Path(artifact).stem, config)
        classification = _classify_target(artifact, config)
        compile_flags: List[str] = []
        unmapped_flags: List[str] = []
        compile_includes: List[str] = []
        compile_defines: List[str] = []
        for c in compiles:
            compile_includes.extend(c.includes)
            compile_defines.extend(c.defines)
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
        if override:
            classification = override.classification
            if override.alias:
                alias_name = override.alias
            if override.classification == "imported":
                ttype = "imported"
                physical_name = override.imported_target or physical_name
                compiles = []
            elif override.classification == "external":
                alias_name = override.alias
        elif Path(artifact).is_absolute():
            classification = "external"
            alias_name = None
        elif classification != "internal":
            alias_name = None
        sources = make_source_files(compiles)
        # Merge and deduplicate once per target, then sort
        all_includes = compile_includes + (target_mapping.include_dirs if target_mapping else [])
        all_defines = compile_defines + (target_mapping.defines if target_mapping else [])
        all_options = compile_flags + (target_mapping.options if target_mapping else [])
        all_link_libs = target_mapping.link_libs if target_mapping else []
        include_dirs = sorted(set(all_includes))
        defines = sorted(set(all_defines))
        compile_options = sorted(set(all_options))
        link_libs = sorted(set(all_link_libs))
        final_alias = alias_name
        # For external targets, ensure no alias unless explicitly provided by override
        if classification == "external":
            final_alias = override.alias if override and override.alias else None
        # Determine visibility: use mapping's visibility, or default based on type
        final_visibility = target_mapping.visibility if target_mapping else None
        tgt = Target(
            artifact=artifact,
            name=physical_name,
            alias=final_alias,
            type=ttype,
            sources=sources,
            include_dirs=include_dirs,
            defines=defines,
            compile_options=compile_options,
            link_options=[],
            link_libs=link_libs,
            deps=[],
            custom_commands=[],
            visibility=final_visibility,
        )
        # External or imported targets should not carry sources
        if classification in {"external", "imported"}:
            tgt.sources = []
        artifact_map[artifact] = tgt
        targets.append(tgt)
    attach_dependencies(targets, facts.rules, artifact_map)
    attach_custom_commands(targets, facts.custom_commands, artifact_map)
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


def attach_dependencies(targets: List[Target], rules: List[EvaluatedRule], artifact_map: Dict[str, Target]) -> None:
    name_lookup: Dict[str, Target] = {}
    for artifact, tgt in artifact_map.items():
        name_lookup[Path(artifact).name] = tgt
        name_lookup[Path(artifact).stem] = tgt
        name_lookup[tgt.name] = tgt
    for tgt in targets:
        deps: List[str] = []
        for rule in rules:
            if not _rule_matches_target(rule, tgt):
                continue
            for prereq in rule.prerequisites:
                dep_tgt = name_lookup.get(Path(prereq).name) or name_lookup.get(Path(prereq).stem)
                if dep_tgt:
                    dep_name = dep_tgt.alias or dep_tgt.name
                    if dep_name not in deps:
                        deps.append(dep_name)
        tgt.deps = sorted(deps)


def attach_custom_commands(targets: List[Target], custom_rules: List[EvaluatedRule], artifact_map: Dict[str, Target]) -> None:
    """Attach custom commands to targets that produce them."""
    name_lookup: Dict[str, Target] = {}
    for artifact, tgt in artifact_map.items():
        name_lookup[Path(artifact).name] = tgt
        name_lookup[Path(artifact).stem] = tgt
        name_lookup[tgt.name] = tgt

    for tgt in targets:
        custom_commands: List[CustomCommand] = []
        for rule in custom_rules:
            if not _rule_matches_target(rule, tgt):
                continue
            # Convert EvaluatedRule to CustomCommand
            commands = [cmd.raw for cmd in rule.commands] if rule.commands else []
            cc = CustomCommand(
                name=f"{tgt.name}_custom",
                targets=rule.targets,
                prerequisites=rule.prerequisites,
                commands=commands,
                outputs=rule.targets,
                inputs=rule.prerequisites,
            )
            custom_commands.append(cc)
        tgt.custom_commands = custom_commands


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


def _classify_target(artifact: str, config: ConfigModel) -> str:
    stem = Path(artifact).stem
    override = classify_library_override(stem, config)
    if override:
        return override.classification
    if Path(artifact).is_absolute():
        return "external"
    return "internal"


def _rule_matches_target(rule: EvaluatedRule, target: Target) -> bool:
    target_names = {target.name, Path(target.artifact).name, Path(target.artifact).stem}
    return any(name in target_names for name in rule.targets)
