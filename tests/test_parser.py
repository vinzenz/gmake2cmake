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
    patterns = [n for n in result.ast if isinstance(n, parser.PatternRule)]
    assert includes[0].optional is False
    assert patterns


def test_line_continuations_and_comments():
    content = "VAR = one \\\n two # trailing\n# whole comment\n"
    result = parser.parse_makefile(content, "Makefile")
    assigns = [n for n in result.ast if isinstance(n, parser.VariableAssign)]
    assert assigns[0].value == "one  two"


def test_parse_conditionals_nested():
    content = """ifeq ($(MODE),debug)
VAR = DEBUG
foo: foo.c
\tgcc -c $< -o $@
else
bar: bar.c
\t@echo skip
endif
"""
    result = parser.parse_makefile(content, "Makefile")
    cond = next(n for n in result.ast if isinstance(n, parser.Conditional))
    assert isinstance(cond.true_body[0], parser.VariableAssign)
    assert isinstance(cond.true_body[1], parser.Rule)
    assert cond.false_body and isinstance(cond.false_body[0], parser.Rule)


def test_parse_unknown_syntax_records_unknown_construct():
    content = "???\n"
    result = parser.parse_makefile(content, "Makefile")
    assert result.unknown_constructs
    uc = result.unknown_constructs[0]
    assert uc.category == "make_syntax"
    assert uc.file == "Makefile"
    assert any(d["code"] == "UNKNOWN_CONSTRUCT" for d in result.diagnostics)
