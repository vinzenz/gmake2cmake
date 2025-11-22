from __future__ import annotations

from dataclasses import replace
from typing import List

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.introspection_parser import IntrospectionData
from gmake2cmake.ir.builder import Project, Target


def reconcile(project: Project, data: IntrospectionData, diagnostics: DiagnosticCollector) -> Project:
    """Merge introspection data into an existing project."""
    targets_by_name = {t.name: t for t in project.targets}
    validated: List[Target] = []
    for tgt in project.targets:
        intro = data.targets.get(tgt.name)
        if intro is None or intro.phony:
            validated.append(tgt)
            continue
        deps_introspected = sorted(intro.prerequisites)
        deps_static = sorted(tgt.deps)
        commands_introspected = list(intro.commands)
        commands_match = commands_introspected == getattr(tgt, "introspection_commands", [])
        deps_match = deps_introspected == deps_static
        if deps_match and commands_match:
            validated.append(_with_introspection(tgt, commands_introspected, validated_by=True))
            continue
        add(
            diagnostics,
            "WARN",
            "INTROSPECTION_MISMATCH",
            f"Target {tgt.name} differs between static and introspection (deps static={deps_static}, introspected={deps_introspected})",
        )
        updated = replace(
            tgt,
            deps=deps_introspected,
            introspection_commands=commands_introspected,
            validated_by_introspection=False,
        )
        validated.append(updated)

    # Add introspection-only targets
    for name, intro in data.targets.items():
        if intro.phony or name in targets_by_name:
            continue
        new_target = Target(
            artifact=name,
            name=name,
            alias=None,
            type="executable",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=sorted(intro.prerequisites),
            custom_commands=[],
            visibility=None,
            introspection_commands=list(intro.commands),
            validated_by_introspection=True,
            origin="introspection",
        )
        validated.append(new_target)

    validated_sorted = sorted(validated, key=lambda t: t.name)
    return replace(project, targets=validated_sorted)


def _with_introspection(target: Target, commands: list[str], validated_by: bool) -> Target:
    return replace(
        target,
        introspection_commands=commands,
        validated_by_introspection=validated_by,
    )
