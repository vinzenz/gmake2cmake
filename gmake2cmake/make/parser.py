from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from gmake2cmake.diagnostics import DiagnosticCollector, add


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
    i = 0
    pending_conditionals: List[tuple[str, List[ASTNode], SourceLocation]] = []

    while i < len(lines):
        raw_line = lines[i]
        line_num = i + 1
        line = _join_continuations(raw_line, lines, i)
        loc = SourceLocation(path=path, line=line_num, column=1)
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("include") or stripped.startswith("-include"):
            optional = stripped.startswith("-include")
            parts = stripped.split()[1:]
            ast.append(IncludeStmt(paths=parts, optional=optional, location=loc))
        elif _is_conditional_start(stripped):
            pending_conditionals.append((stripped, [], loc))
        elif stripped == "else":
            if not pending_conditionals:
                add_diagnostic(diagnostics, "ERROR", "PARSER_CONDITIONAL", "Unmatched else", loc)
            else:
                cond = pending_conditionals.pop()
                pending_conditionals.append((cond[0] + " ELSE", cond[1], loc))
        elif stripped == "endif":
            if not pending_conditionals:
                add_diagnostic(diagnostics, "ERROR", "PARSER_CONDITIONAL", "Unmatched endif", loc)
            else:
                cond_test, true_body, cond_loc = pending_conditionals.pop()
                false_body: List[ASTNode] = []
                if " ELSE" in cond_test:
                    # last stored location is else
                    else_loc = loc
                    false_body = cond_loc.true_body if isinstance(cond_loc, Conditional) else []
                ast.append(Conditional(test=cond_test, true_body=true_body, false_body=false_body, location=cond_loc))
        elif ":" in stripped and not stripped.startswith("\t"):
            target_part, prereq_part = stripped.split(":", 1)
            targets = target_part.strip().split()
            prereqs = prereq_part.strip().split()
            commands, next_index = parse_commands(lines, i + 1, path)
            node = Rule(targets=targets, prerequisites=prereqs, commands=commands, location=loc)
            ast.append(node)
            i = next_index
            continue
        elif "=" in stripped:
            name, value = stripped.split("=", 1)
            kind = "simple"
            if ":=" in stripped:
                name, value = stripped.split(":=", 1)
                kind = "recursive"
            elif "+=" in stripped:
                name, value = stripped.split("+=", 1)
                kind = "append"
            ast.append(VariableAssign(name=name.strip(), value=value.strip(), kind=kind, location=loc))
        elif stripped.startswith("\t"):
            ast.append(RawCommand(command=stripped.lstrip("\t"), location=loc))
        i += 1

    return ParseResult(ast=ast, diagnostics=diagnostics)


def parse_commands(lines: List[str], start_index: int, path: str) -> tuple[List[str], int]:
    commands: List[str] = []
    i = start_index
    while i < len(lines) and lines[i].startswith("\t"):
        commands.append(lines[i].lstrip("\t"))
        i += 1
    return commands, i


def _join_continuations(line: str, lines: List[str], index: int) -> str:
    result = line.rstrip("\n")
    while result.endswith("\\") and index + 1 < len(lines):
        result = result[:-1] + lines[index + 1].rstrip("\n")
        index += 1
    return result


def _is_conditional_start(stripped: str) -> bool:
    return stripped.startswith(("ifeq", "ifneq", "ifdef", "ifndef"))


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
