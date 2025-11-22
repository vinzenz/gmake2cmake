from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class ParsedTarget:
    name: str
    prerequisites: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    phony: bool = False


@dataclass
class IntrospectionData:
    targets: Dict[str, ParsedTarget]
    variables: Dict[str, str]


_BUILTIN_SECTION = "# Built-in"


def parse_dump(dump: str) -> IntrospectionData:
    targets: Dict[str, ParsedTarget] = {}
    variables: Dict[str, str] = {}
    lines = dump.splitlines()
    in_rules = False
    current_target: ParsedTarget | None = None

    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith(_BUILTIN_SECTION):
            break
        if not line:
            continue
        if line.startswith("# Variables"):
            in_rules = False
            current_target = None
            continue
        if line.startswith("# Files"):
            in_rules = True
            current_target = None
            continue

        if in_rules:
            if not line.startswith("\t") and ":" in line:
                target_part, _, prereq_part = line.partition(":")
                name = target_part.strip()
                prereqs = [p.strip() for p in prereq_part.split() if p.strip()]
                normalized_name = _normalize(name)
                current_target = ParsedTarget(name=normalized_name, prerequisites=_normalize_list(prereqs))
                targets[normalized_name] = current_target
                continue
            if current_target and line.startswith("\t"):
                cmd = line.lstrip("\t")
                current_target.commands.append(cmd)
        else:
            if "=" in line and not line.startswith("\t"):
                key, _, val = line.partition("=")
                variables[key.strip()] = val.strip()

    # Mark .PHONY
    phony_list = targets.pop(".PHONY", None)
    if phony_list:
        for name in phony_list.prerequisites:
            tgt = targets.get(_normalize(name))
            if tgt:
                tgt.phony = True
            else:
                targets[_normalize(name)] = ParsedTarget(
                    name=_normalize(name), prerequisites=[], commands=[], phony=True
                )
    ordered_targets = dict(sorted(targets.items(), key=lambda kv: kv[0]))
    ordered_vars = dict(sorted(variables.items(), key=lambda kv: kv[0]))
    return IntrospectionData(targets=ordered_targets, variables=ordered_vars)


def _normalize(path: str) -> str:
    return Path(path).as_posix()


def _normalize_list(items: List[str]) -> List[str]:
    return [_normalize(item) for item in items]
