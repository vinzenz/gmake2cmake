from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gmake2cmake.config import ConfigModel, should_ignore_path
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.unknowns import UnknownConstruct
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
    unknown_constructs: List[UnknownConstruct] = field(default_factory=list)


def evaluate_ast(nodes: List[parser.ASTNode], env: VariableEnv, config: ConfigModel, diagnostics: DiagnosticCollector) -> BuildFacts:
    facts = BuildFacts()
    has_seen_rule = False
    global_files = {Path(name).name for name in config.global_config_files}

    def _process(nodes: List[parser.ASTNode]) -> None:
        nonlocal has_seen_rule
        for node in nodes:
            if isinstance(node, parser.VariableAssign):
                if should_ignore_path(node.location.path, config):
                    continue
                value = expand_variables(node.value, env, node.location, diagnostics)
                if node.kind == "append":
                    env.append(node.name, value)
                elif node.kind == "recursive":
                    env.set_recursive(node.name, value)
                else:
                    env.set_simple(node.name, value)
                if (not has_seen_rule) or (Path(node.location.path).name in global_files):
                    _record_global(node, value, facts)
            elif isinstance(node, parser.Conditional):
                chosen = _evaluate_conditional(node, env, diagnostics)
                if chosen:
                    _process(chosen)
            elif isinstance(node, parser.Rule):
                if _rule_ignored(node, config):
                    continue
                has_seen_rule = True
                facts.rules.append(expand_rule(node, env, diagnostics))
            elif isinstance(node, parser.PatternRule):
                if _rule_ignored(node, config):
                    continue
                has_seen_rule = True
                facts.rules.append(expand_rule(node, env, diagnostics, is_pattern=True))
            elif isinstance(node, parser.RawCommand):
                if should_ignore_path(node.location.path, config):
                    continue
                ev_cmd = EvaluatedCommand(
                    raw=node.command,
                    expanded=expand_variables(node.command, env, node.location, diagnostics),
                    location=node.location,
                )
                facts.custom_commands.append(
                    EvaluatedRule(targets=[], prerequisites=[], commands=[ev_cmd], is_pattern=False, location=node.location)
                )
            elif isinstance(node, parser.IncludeStmt):
                # includes handled by discoverer; treat as provenance for globals
                if not has_seen_rule and not should_ignore_path(node.location.path, config):
                    _record_global(
                        parser.VariableAssign(name="INCLUDE", value=" ".join(node.paths), kind="simple", location=node.location),
                        " ".join(node.paths),
                        facts,
                    )

    _process(nodes)
    facts.inferred_compiles.extend(infer_compiles(facts.rules, config, diagnostics))
    build_rules, custom_rules = separate_custom_commands(facts.rules)
    facts.rules = build_rules
    facts.custom_commands.extend(custom_rules)
    facts.diagnostics = diagnostics.diagnostics
    return facts


def expand_variables(
    value: str,
    env: VariableEnv,
    location: parser.SourceLocation,
    diagnostics: DiagnosticCollector,
    auto_vars: Optional[Dict[str, str]] = None,
) -> str:
    result = ""
    i = 0
    seen = set()
    auto_vars = auto_vars or {}
    while i < len(value):
        if value[i] == "$" and i + 1 < len(value) and value[i + 1] not in {"(", "{"}:
            var_key = value[i + 1]
            result += auto_vars.get(var_key, env.get(var_key))
            i += 2
            continue
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
            replacement, was_func = _replace_var(var_name, env, auto_vars)
            if was_func:
                add(diagnostics, "WARN", "EVAL_UNSUPPORTED_FUNC", f"Unsupported make function {var_name} at {location.path}:{location.line}")
            result += replacement
            i = end + 1
        else:
            result += value[i]
            i += 1
    return result


def expand_rule(rule: parser.Rule | parser.PatternRule, env: VariableEnv, diagnostics: DiagnosticCollector, is_pattern: bool = False) -> EvaluatedRule:
    targets_raw = getattr(rule, "targets", [getattr(rule, "target_pattern", "")])
    prereqs_attr = getattr(rule, "prerequisites", getattr(rule, "prereq_patterns", []))
    targets = [expand_variables(t, env, rule.location, diagnostics) for t in targets_raw]
    prerequisites = [expand_variables(p, env, rule.location, diagnostics) for p in prereqs_attr]
    auto_vars = _auto_vars(targets, prerequisites)
    commands = [
        EvaluatedCommand(raw=cmd, expanded=expand_variables(cmd, env, rule.location, diagnostics, auto_vars=auto_vars), location=rule.location)
        for cmd in rule.commands
    ]
    return EvaluatedRule(targets=targets, prerequisites=prerequisites, commands=commands, is_pattern=is_pattern, location=rule.location)


def infer_compiles(rules: List[EvaluatedRule], config: ConfigModel, diagnostics: DiagnosticCollector) -> List[InferredCompile]:
    compiles: List[InferredCompile] = []
    for rule in rules:
        for cmd in rule.commands:
            if not _looks_like_compile(cmd.expanded):
                continue
            src = _extract_flag(cmd.expanded, "-c") or (rule.prerequisites[0] if rule.prerequisites else "")
            out = _extract_flag(cmd.expanded, "-o") or (rule.targets[0] if rule.targets else "")
            includes = _extract_flags(cmd.expanded, "-I")
            defines = _extract_flags(cmd.expanded, "-D")
            if should_ignore_path(src, config) or should_ignore_path(out, config):
                continue
            if not src:
                add(diagnostics, "WARN", "EVAL_NO_SOURCE", f"Could not infer source for rule at {cmd.location.path}:{cmd.location.line}")
            lang = _guess_lang(cmd.expanded, src)
            skip_flags = set(includes + defines + ["-c"])
            flags = [f for f in cmd.expanded.split() if f.startswith("-") and f not in skip_flags and not f.startswith("-o")]
            compiles.append(
                InferredCompile(
                    source=src,
                    output=out,
                    language=lang,
                    flags=flags,
                    includes=includes,
                    defines=defines,
                    location=cmd.location,
                )
            )
    return compiles


def _looks_like_compile(cmd: str) -> bool:
    tokens = cmd.split()
    if not tokens:
        return False
    compiler_prefixes = ("cc", "gcc", "clang", "c++", "g++", "clang++")
    return tokens[0].endswith(compiler_prefixes) or tokens[0] in compiler_prefixes or "-c" in tokens


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
    tokens = cmd.split()
    compiler = tokens[0] if tokens else ""
    if compiler.endswith(("c++", "g++", "clang++")) or compiler in {"c++", "g++", "clang++"} or "++" in compiler:
        return "cpp"
    ext = Path(src).suffix.lower()
    if ext in {".cpp", ".cc", ".cxx"}:
        return "cpp"
    if ext in {".s", ".asm"}:
        return "asm"
    return "c"


def _rule_ignored(rule: parser.Rule | parser.PatternRule, config: ConfigModel) -> bool:
    for tgt in getattr(rule, "targets", [getattr(rule, "target_pattern", "")]):
        if should_ignore_path(tgt, config):
            return True
    for prereq in getattr(rule, "prerequisites", getattr(rule, "prereq_patterns", [])):
        if should_ignore_path(prereq, config):
            return True
    return False


def _auto_vars(targets: List[str], prerequisites: List[str]) -> Dict[str, str]:
    first_target = targets[0] if targets else ""
    first_prereq = prerequisites[0] if prerequisites else ""
    merged_prereqs = " ".join(dict.fromkeys(prerequisites))
    return {
        "@": first_target,
        "<": first_prereq,
        "^": merged_prereqs,
        "?": merged_prereqs,
        "+": " ".join(prerequisites),
        "*": Path(first_target).stem if first_target else "",
    }


def _evaluate_conditional(node: parser.Conditional, env: VariableEnv, diagnostics: DiagnosticCollector) -> List[parser.ASTNode]:
    test = node.test.strip()
    if test.startswith("ifeq"):
        lhs, rhs = _split_conditional_args(test[len("ifeq") :], env, diagnostics, node.location)
        return node.true_body if lhs == rhs else node.false_body
    if test.startswith("ifneq"):
        lhs, rhs = _split_conditional_args(test[len("ifneq") :], env, diagnostics, node.location)
        return node.false_body if lhs == rhs else node.true_body
    if test.startswith("ifdef"):
        name = test[len("ifdef") :].strip(" ()")
        return node.true_body if env.get(name) else node.false_body
    if test.startswith("ifndef"):
        name = test[len("ifndef") :].strip(" ()")
        return node.false_body if env.get(name) else node.true_body
    add(diagnostics, "WARN", "EVAL_UNSUPPORTED_FUNC", f"Unsupported conditional {test} at {node.location.path}:{node.location.line}")
    return node.true_body


def _split_conditional_args(expr: str, env: VariableEnv, diagnostics: DiagnosticCollector, loc: parser.SourceLocation) -> Tuple[str, str]:
    raw = expr.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    if "," in raw:
        left, right = raw.split(",", 1)
    else:
        parts = raw.split(None, 1)
        left, right = (parts + [""])[:2]
    left_val = expand_variables(left.strip().strip('"').strip("'"), env, loc, diagnostics)
    right_val = expand_variables(right.strip().strip('"').strip("'"), env, loc, diagnostics)
    return left_val, right_val


def _replace_var(var_name: str, env: VariableEnv, auto_vars: Dict[str, str]) -> Tuple[str, bool]:
    if var_name in auto_vars:
        return auto_vars[var_name], False
    if " " in var_name or "," in var_name:
        return "", True
    return env.get(var_name), False


def _looks_like_feature_toggle(name: str, value: str) -> bool:
    value_lower = value.lower()
    boolish = {"1", "0", "on", "off", "yes", "no", "true", "false"}
    return name.startswith(("WITH_", "ENABLE_", "USE_", "HAVE_")) or value_lower in boolish


def _coerce_bool(value: str) -> bool | str:
    lowered = value.lower()
    if lowered in {"1", "on", "yes", "true"}:
        return True
    if lowered in {"0", "off", "no", "false"}:
        return False
    return value


def _append_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _record_global(var_node: parser.VariableAssign, value: str, facts: BuildFacts) -> None:
    facts.project_globals.vars[var_node.name] = value
    _append_unique(facts.project_globals.sources, var_node.location.path)
    tokens = value.split()
    if var_node.name.upper() in {"CFLAGS", "CPPFLAGS"}:
        facts.project_globals.flags.setdefault("c", []).extend(tokens)
    elif var_node.name.upper() == "CXXFLAGS":
        facts.project_globals.flags.setdefault("cpp", []).extend(tokens)
    elif var_node.name.upper() == "LDFLAGS":
        facts.project_globals.flags.setdefault("link", []).extend(tokens)
    for tok in tokens:
        if tok.startswith("-I"):
            _append_unique(facts.project_globals.includes, tok[len("-I") :])
        elif tok.startswith("-D"):
            _append_unique(facts.project_globals.defines, tok[len("-D") :])
    if _looks_like_feature_toggle(var_node.name, value):
        facts.project_globals.feature_toggles[var_node.name] = _coerce_bool(value)


def separate_custom_commands(rules: List[EvaluatedRule]) -> Tuple[List[EvaluatedRule], List[EvaluatedRule]]:
    build_rules: List[EvaluatedRule] = []
    custom_rules: List[EvaluatedRule] = []
    for rule in rules:
        if any(_looks_like_compile(cmd.expanded) for cmd in rule.commands):
            build_rules.append(rule)
        else:
            custom_rules.append(rule)
    return build_rules, custom_rules
