from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from gmake2cmake.ir.unknowns import UnknownConstruct, UnknownConstructFactory
from gmake2cmake.types import DiagnosticDict


@dataclass
class ParseContext:
    """Context object carrying diagnostics, unknowns, and factory.

    Attributes:
        diagnostics: List of diagnostic dictionaries
        unknowns: List of unknown constructs encountered
        factory: Factory for creating unknown construct instances
        path: File path being parsed
    """

    diagnostics: List[DiagnosticDict]
    unknowns: List[UnknownConstruct]
    factory: UnknownConstructFactory
    path: str


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
    """Result of parsing a makefile.

    Attributes:
        ast: List of parsed AST nodes
        diagnostics: List of diagnostic messages as dictionaries
        unknown_constructs: List of unknown constructs encountered
    """

    ast: List[ASTNode]
    diagnostics: List[DiagnosticDict]
    unknown_constructs: List[UnknownConstruct]


def parse_makefile(content: str, path: str, unknown_factory: UnknownConstructFactory | None = None) -> ParseResult:
    lines = content.splitlines()
    factory = unknown_factory or UnknownConstructFactory()
    context = ParseContext(
        diagnostics=[],
        unknowns=[],
        factory=factory,
        path=path,
    )
    ast = _parse_lines(lines, 0, len(lines), context)
    return ParseResult(ast=ast, diagnostics=context.diagnostics, unknown_constructs=context.unknowns)


def _parse_lines(lines: List[str], start_index: int, end_index: int, context: ParseContext) -> List[ASTNode]:
    """Parse lines in the given range, returning list of AST nodes."""
    ast: List[ASTNode] = []
    index = start_index

    while index < end_index:
        line, loc, index = _consume_line(lines, index, context.path)
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if _is_conditional_start(stripped):
            conditional, index = _parse_conditional(lines, index, context)
            ast.append(conditional)
            index += 1
        else:
            node, index = _parse_statement(stripped, lines, index, context, loc)
            if node is not None:
                ast.append(node)
            index += 1

    return ast


def _consume_line(lines: List[str], index: int, path: str) -> Tuple[str, SourceLocation, int]:
    start_line = index + 1
    joined, end_index = _join_continuations(lines, index)
    stripped_comment = _strip_comment(joined)
    return stripped_comment, SourceLocation(path=path, line=start_line, column=1), end_index


def _parse_statement(
    stripped: str,
    lines: List[str],
    index: int,
    context: ParseContext,
    loc: SourceLocation,
) -> tuple[ASTNode | None, int]:
    """Parse a statement and return (node, new_index)."""
    if stripped.startswith("include") or stripped.startswith("-include"):
        return _parse_include_statement(stripped, loc), index
    if any(op in stripped for op in (":=", "+=", "=")):
        return _parse_assignment(stripped, loc), index
    if ":" in stripped and not stripped.startswith("\t"):
        return _parse_rule(stripped, lines, index, context, loc)
    if stripped.startswith("\t"):
        return RawCommand(command=stripped.lstrip("\t"), location=loc), index
    # Unknown or unsupported syntax
    return _handle_unknown_construct(stripped, context, loc), index


def _parse_include_statement(stripped: str, loc: SourceLocation) -> IncludeStmt:
    """Extract and return include statement."""
    optional = stripped.startswith("-include")
    parts = stripped.split()[1:]
    return IncludeStmt(paths=parts, optional=optional, location=loc)


def _parse_assignment(stripped: str, loc: SourceLocation) -> VariableAssign | None:
    """Parse variable assignment (=, :=, +=). Returns None if ':' in name (rule syntax)."""
    if ":=" in stripped:
        name, value = stripped.split(":=", 1)
        kind = "recursive"
    elif "+=" in stripped:
        name, value = stripped.split("+=", 1)
        kind = "append"
    else:
        name, value = stripped.split("=", 1)
        kind = "simple"
    # Avoid confusing rule syntax containing ':' with assignment
    if ":" not in name:
        return VariableAssign(name=name.strip(), value=value.strip(), kind=kind, location=loc)
    return None


def _parse_rule(stripped: str, lines: List[str], index: int, context: ParseContext, loc: SourceLocation) -> tuple[PatternRule | Rule, int]:
    """Parse a rule with optional pattern matching."""
    target_part, prereq_part = stripped.split(":", 1)
    targets = target_part.strip().split()
    prereqs = prereq_part.strip().split()
    commands, next_index = parse_commands(lines, index + 1, context.path)
    is_pattern = any("%" in tgt for tgt in targets)
    rule_cls = PatternRule if is_pattern else Rule
    node = rule_cls(targets[0] if is_pattern else targets, prereqs if prereqs else [], commands, loc)
    return node, next_index - 1


def _handle_unknown_construct(stripped: str, context: ParseContext, loc: SourceLocation) -> None:
    """Record unknown construct as diagnostic and unknown."""
    uc = context.factory.create(
        category="make_syntax",
        file=context.path,
        line=loc.line,
        column=loc.column,
        raw_snippet=stripped,
        normalized_form=stripped,
        impact={"phase": "parse", "severity": "warning"},
        suggested_action="manual_review",
    )
    context.unknowns.append(uc)
    add_diagnostic(context.diagnostics, "WARN", "UNKNOWN_CONSTRUCT", f"{uc.id}: Unknown syntax", loc)
    return None


def _parse_conditional(lines: List[str], start_index: int, context: ParseContext) -> tuple[Conditional, int]:
    header, loc, index = _consume_line(lines, start_index, context.path)
    test = header.strip()
    true_body: List[ASTNode] = []
    false_body: List[ASTNode] = []
    in_false = False
    index += 1

    while index < len(lines):
        line, line_loc, index = _consume_line(lines, index, context.path)
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if _is_conditional_start(stripped):
            nested, index = _parse_conditional(lines, index, context)
            (false_body if in_false else true_body).append(nested)
            index += 1
        elif stripped == "else":
            in_false = True
            index += 1
        elif stripped == "endif":
            return Conditional(test=test, true_body=true_body, false_body=false_body, location=loc), index
        else:
            node, index = _parse_statement(stripped, lines, index, context, line_loc)
            if node is not None:
                (false_body if in_false else true_body).append(node)
            index += 1

    add_diagnostic(context.diagnostics, "ERROR", "PARSER_CONDITIONAL", "Unmatched conditional block", loc)
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


def add_diagnostic(diagnostics: List[DiagnosticDict], severity: str, code: str, message: str, loc: SourceLocation) -> None:
    """Add a diagnostic to the diagnostics list.

    Args:
        diagnostics: List of diagnostic dictionaries to append to
        severity: Severity level ('ERROR', 'WARN', 'INFO')
        code: Diagnostic code identifier
        message: Human-readable diagnostic message
        loc: Source location information

    Returns:
        None
    """
    diag: DiagnosticDict = {
        "severity": severity,
        "code": code,
        "message": message,
        "location": f"{loc.path}:{loc.line}",
        "origin": None,
    }
    diagnostics.append(diag)


def normalize_tokens(token: str) -> str:
    return " ".join(token.split())
