from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from gmake2cmake.config import ConfigModel
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.make import parser


@dataclass
class VariableEnv:
    values: Dict[str, str] = field(default_factory=dict)

    def set_simple(self, name: str, value: str) -> None:
        self.values[name] = value

    def set_recursive(self, name: str, value: str) -> None:
        self.values[name] = value

    def append(self, name: str, value: str) -> None:
        self.values[name] = self.values.get(name, "") + value

    def get(self, name: str) -> str:
        return self.values.get(name, "")


@dataclass
class EvaluatedCommand:
    raw: str
    expanded: str
    location: parser.SourceLocation


@dataclass
class EvaluatedRule:
    targets: List[str]
    prerequisites: List[str]
    commands: List[EvaluatedCommand]
    is_pattern: bool
    location: parser.SourceLocation


@dataclass
class InferredCompile:
    source: str
    output: str
    language: str
    flags: List[str]
    includes: List[str]
    defines: List[str]
    location: parser.SourceLocation


@dataclass
class ProjectGlobals:
    vars: Dict[str, str] = field(default_factory=dict)
    flags: Dict[str, List[str]] = field(default_factory=dict)
    defines: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    feature_toggles: Dict[str, str | bool] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)


@dataclass
class BuildFacts:
    rules: List[EvaluatedRule] = field(default_factory=list)
    inferred_compiles: List[InferredCompile] = field(default_factory=list)
    custom_commands: List[EvaluatedRule] = field(default_factory=list)
    project_globals: ProjectGlobals = field(default_factory=ProjectGlobals)
    diagnostics: List = field(default_factory=list)


def evaluate_ast(nodes: List[parser.ASTNode], env: VariableEnv, config: ConfigModel, diagnostics: DiagnosticCollector) -> BuildFacts:
    facts = BuildFacts()
    has_seen_rule = False
    global_files = {name for name in config.global_config_files}

    for node in nodes:
        if isinstance(node, parser.VariableAssign):
            value = expand_variables(node.value, env, node.location, diagnostics)
            if node.kind == "append":
                env.append(node.name, value)
            elif node.kind == "recursive":
                env.set_recursive(node.name, value)
            else:
                env.set_simple(node.name, value)
            if not has_seen_rule and (node.location.path.split("/")[-1] in global_files):
                _record_global(node, value, facts)
        elif isinstance(node, parser.Rule):
            has_seen_rule = True
            ev_rule = expand_rule(node, env, diagnostics)
            facts.rules.append(ev_rule)
        elif isinstance(node, parser.PatternRule):
            has_seen_rule = True
            ev_rule = expand_rule(node, env, diagnostics, is_pattern=True)
            facts.rules.append(ev_rule)
        elif isinstance(node, parser.RawCommand):
            ev_cmd = EvaluatedCommand(raw=node.command, expanded=expand_variables(node.command, env, node.location, diagnostics), location=node.location)
            facts.custom_commands.append(
                EvaluatedRule(targets=[], prerequisites=[], commands=[ev_cmd], is_pattern=False, location=node.location)
            )
        elif isinstance(node, parser.Conditional):
            # simple handling: evaluate true body only
            facts_true = evaluate_ast(node.true_body, env, config, diagnostics)
            facts.rules.extend(facts_true.rules)
            facts.inferred_compiles.extend(facts_true.inferred_compiles)
            facts.custom_commands.extend(facts_true.custom_commands)
    facts.inferred_compiles.extend(infer_compiles(facts.rules, config, diagnostics))
    return facts


def expand_variables(value: str, env: VariableEnv, location: parser.SourceLocation, diagnostics: DiagnosticCollector) -> str:
    result = ""
    i = 0
    seen = set()
    while i < len(value):
        if value[i] == "$" and i + 1 < len(value) and value[i + 1] in {"(", "{"}:
            end = value.find(")", i + 2) if value[i + 1] == "(" else value.find("}", i + 2)
            if end == -1:
                add(diagnostics, "ERROR", "EVAL_RECURSIVE_LOOP", f"Unclosed variable at {location.path}:{location.line}")
                break
            var_name = value[i + 2 : end]
            if var_name in seen:
                add(diagnostics, "ERROR", "EVAL_RECURSIVE_LOOP", f"Recursive variable {var_name} at {location.path}:{location.line}")
                break
            seen.add(var_name)
            result += env.get(var_name)
            i = end + 1
        else:
            result += value[i]
            i += 1
    return result


def expand_rule(rule: parser.Rule | parser.PatternRule, env: VariableEnv, diagnostics: DiagnosticCollector, is_pattern: bool = False) -> EvaluatedRule:
    targets = [expand_variables(t, env, rule.location, diagnostics) for t in getattr(rule, "targets", [getattr(rule, "target_pattern", "")])]
    prereqs_attr = getattr(rule, "prerequisites", getattr(rule, "prereq_patterns", []))
    prerequisites = [expand_variables(p, env, rule.location, diagnostics) for p in prereqs_attr]
    commands = [
        EvaluatedCommand(raw=cmd, expanded=expand_variables(cmd, env, rule.location, diagnostics), location=rule.location)
        for cmd in rule.commands
    ]
    return EvaluatedRule(targets=targets, prerequisites=prerequisites, commands=commands, is_pattern=is_pattern, location=rule.location)


def infer_compiles(rules: List[EvaluatedRule], config: ConfigModel, diagnostics: DiagnosticCollector) -> List[InferredCompile]:
    compiles: List[InferredCompile] = []
    for rule in rules:
        for cmd in rule.commands:
            if _looks_like_compile(cmd.expanded):
                src = _extract_flag(cmd.expanded, "-c") or ""
                out = _extract_flag(cmd.expanded, "-o") or ""
                lang = _guess_lang(cmd.expanded, src)
                includes = _extract_flags(cmd.expanded, "-I")
                defines = _extract_flags(cmd.expanded, "-D")
                compiles.append(
                    InferredCompile(
                        source=src,
                        output=out,
                        language=lang,
                        flags=[f for f in cmd.expanded.split() if f.startswith("-") and f not in includes and f not in defines],
                        includes=includes,
                        defines=defines,
                        location=cmd.location,
                    )
                )
            else:
                continue
    return compiles


def _looks_like_compile(cmd: str) -> bool:
    tokens = cmd.split()
    if not tokens:
        return False
    compiler_prefixes = ("cc", "gcc", "clang", "c++", "g++", "clang++")
    return tokens[0].endswith(compiler_prefixes) or tokens[0] in compiler_prefixes


def _extract_flag(cmd: str, flag: str) -> Optional[str]:
    tokens = cmd.split()
    for i, t in enumerate(tokens):
        if t == flag and i + 1 < len(tokens):
            return tokens[i + 1]
        if t.startswith(flag):
            return t[len(flag) :]
    return None


def _extract_flags(cmd: str, flag: str) -> List[str]:
    values: List[str] = []
    tokens = cmd.split()
    for i, t in enumerate(tokens):
        if t == flag and i + 1 < len(tokens):
            values.append(tokens[i + 1])
        elif t.startswith(flag):
            values.append(t[len(flag) :])
    return values


def _guess_lang(cmd: str, src: str) -> str:
    if src.endswith(".c"):
        return "c"
    if src.endswith((".cpp", ".cc", ".cxx")):
        return "cpp"
    if src.endswith(".s") or src.endswith(".asm"):
        return "asm"
    if "++" in cmd or cmd.startswith(("c++", "g++", "clang++")):
        return "cpp"
    return "c"


def _record_global(var_node: parser.VariableAssign, value: str, facts: BuildFacts) -> None:
    facts.project_globals.vars[var_node.name] = value
    facts.project_globals.sources.append(var_node.location.path)
