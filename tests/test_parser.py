from __future__ import annotations

from gmake2cmake.make import parser


def test_parse_assignments_and_rules():
    content = "VAR = 1\nfoo: bar baz\n\tcc -c foo.c -o foo.o\n"
    result = parser.parse_makefile(content, "Makefile")
    assigns = [n for n in result.ast if isinstance(n, parser.VariableAssign)]
    rules = [n for n in result.ast if isinstance(n, parser.Rule)]
    assert assigns[0].name == "VAR"
    assert rules[0].targets == ["foo"]
    assert rules[0].commands[0] == "cc -c foo.c -o foo.o"


def test_parse_pattern_rule_and_include():
    content = "include inc.mk\n%.o: %.c\n\tcc -c $< -o $@\n"
    result = parser.parse_makefile(content, "Makefile")
    includes = [n for n in result.ast if isinstance(n, parser.IncludeStmt)]
    patterns = [n for n in result.ast if isinstance(n, parser.Rule)]
    assert includes[0].optional is False
    assert patterns


def test_line_continuations():
    content = "VAR = one \\\n two\n"
    result = parser.parse_makefile(content, "Makefile")
    assigns = [n for n in result.ast if isinstance(n, parser.VariableAssign)]
    assert "two" in assigns[0].value
