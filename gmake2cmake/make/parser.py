from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int
    column: int


@dataclass(frozen=True)
class VariableAssign:
    name: str
    value: str
    kind: str  # simple/recursive/append
    location: SourceLocation


@dataclass(frozen=True)
class Rule:
    targets: List[str]
    prerequisites: List[str]
    commands: List[str]
    location: SourceLocation


@dataclass(frozen=True)
class PatternRule:
    target_pattern: str
    prereq_patterns: List[str]
    commands: List[str]
    location: SourceLocation


@dataclass(frozen=True)
class IncludeStmt:
    paths: List[str]
    optional: bool
    location: SourceLocation


@dataclass(frozen=True)
class Conditional:
    test: str
    true_body: List["ASTNode"]
    false_body: List["ASTNode"]
    location: SourceLocation


@dataclass(frozen=True)
class RawCommand:
    command: str
    location: SourceLocation


ASTNode = VariableAssign | Rule | PatternRule | IncludeStmt | Conditional | RawCommand


@dataclass
class ParseResult:
    ast: List[ASTNode]
    diagnostics: List


def parse_makefile(content: str, path: str) -> ParseResult:
    lines = content.splitlines()
    ast: List[ASTNode] = []
    diagnostics: List = []
    index = 0

    while index < len(lines):
        line, loc, index = _consume_line(lines, index, path)
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if _is_conditional_start(stripped):
            conditional, index = _parse_conditional(lines, index, path, diagnostics)
            ast.append(conditional)
            index += 1
            continue
        node, index = _parse_statement(stripped, lines, index, path, diagnostics, loc)
        if node is not None:
            ast.append(node)
        index += 1

    return ParseResult(ast=ast, diagnostics=diagnostics)


def _consume_line(lines: List[str], index: int, path: str) -> Tuple[str, SourceLocation, int]:
    start_line = index + 1
    joined, end_index = _join_continuations(lines, index)
    stripped_comment = _strip_comment(joined)
    return stripped_comment, SourceLocation(path=path, line=start_line, column=1), end_index


def _parse_statement(stripped: str, lines: List[str], index: int, path: str, diagnostics: List, loc: SourceLocation):
    if stripped.startswith("include") or stripped.startswith("-include"):
        optional = stripped.startswith("-include")
        parts = stripped.split()[1:]
        return IncludeStmt(paths=parts, optional=optional, location=loc), index
    if ":" in stripped and not stripped.startswith("\t"):
        target_part, prereq_part = stripped.split(":", 1)
        targets = target_part.strip().split()
        prereqs = prereq_part.strip().split()
        commands, next_index = parse_commands(lines, index + 1, path)
        is_pattern = any("%" in tgt for tgt in targets)
        rule_cls = PatternRule if is_pattern else Rule
        node = rule_cls(targets[0] if is_pattern else targets, prereqs if prereqs else [], commands, loc)
        return node, next_index - 1
    if "=" in stripped:
        name, value = stripped.split("=", 1)
        kind = "simple"
        if ":=" in stripped:
            name, value = stripped.split(":=", 1)
            kind = "recursive"
        elif "+=" in stripped:
            name, value = stripped.split("+=", 1)
            kind = "append"
        return VariableAssign(name=name.strip(), value=value.strip(), kind=kind, location=loc), index
    if stripped.startswith("\t"):
        return RawCommand(command=stripped.lstrip("\t"), location=loc), index
    return None, index


def _parse_conditional(lines: List[str], start_index: int, path: str, diagnostics: List) -> tuple[Conditional, int]:
    header, loc, index = _consume_line(lines, start_index, path)
    test = header.strip()
    true_body: List[ASTNode] = []
    false_body: List[ASTNode] = []
    in_false = False
    index += 1
    while index < len(lines):
        line, line_loc, index = _consume_line(lines, index, path)
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if _is_conditional_start(stripped):
            nested, index = _parse_conditional(lines, index, path, diagnostics)
            (false_body if in_false else true_body).append(nested)
            index += 1
            continue
        if stripped == "else":
            in_false = True
            index += 1
            continue
        if stripped == "endif":
            return Conditional(test=test, true_body=true_body, false_body=false_body, location=loc), index
        node, index = _parse_statement(stripped, lines, index, path, diagnostics, line_loc)
        if node is not None:
            (false_body if in_false else true_body).append(node)
        index += 1
    add_diagnostic(diagnostics, "ERROR", "PARSER_CONDITIONAL", "Unmatched conditional block", loc)
    return Conditional(test=test, true_body=true_body, false_body=false_body, location=loc), index


def parse_commands(lines: List[str], start_index: int, path: str) -> tuple[List[str], int]:
    commands: List[str] = []
    i = start_index
    while i < len(lines) and lines[i].startswith("\t"):
        commands.append(lines[i].lstrip("\t"))
        i += 1
    return commands, i


def _join_continuations(lines: List[str], index: int) -> tuple[str, int]:
    result = lines[index].rstrip("\n")
    end_index = index
    while result.endswith("\\") and end_index + 1 < len(lines):
        result = result[:-1] + lines[end_index + 1].rstrip("\n")
        end_index += 1
    return result, end_index


def _is_conditional_start(stripped: str) -> bool:
    return stripped.startswith(("ifeq", "ifneq", "ifdef", "ifndef"))


def _strip_comment(line: str) -> str:
    result = ""
    escaped = False
    for ch in line:
        if ch == "\\":
            escaped = not escaped
            result += ch
            continue
        if ch == "#" and not escaped:
            break
        escaped = False
        result += ch
    return result.rstrip()


def add_diagnostic(diagnostics: List, severity: str, code: str, message: str, loc: SourceLocation) -> None:
    diagnostics.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "location": f"{loc.path}:{loc.line}",
        }
    )


def normalize_tokens(token: str) -> str:
    return " ".join(token.split())
