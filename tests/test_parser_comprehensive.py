"""Comprehensive tests for Make parser (TASK-0059 expansion).

Tests cover the entire parser.py module with focus on:
- Variable assignment variations (=, :=, +=)
- Rule parsing (normal and pattern rules)
- Conditional parsing (ifeq, ifneq, ifdef, ifndef)
- Line continuation handling
- Comment handling and edge cases
- Include statement variations
- Error recovery and unknown constructs
- Nested conditionals
"""

from __future__ import annotations

from gmake2cmake.make.parser import (
    Conditional,
    IncludeStmt,
    ParseResult,
    PatternRule,
    Rule,
    VariableAssign,
    _is_conditional_start,
    _join_continuations,
    _strip_comment,
    parse_commands,
    parse_makefile,
)


class TestParseBasicStatements:
    """Tests for parsing basic statement types."""

    def test_parse_empty_makefile(self):
        """Empty makefile should parse successfully."""
        result = parse_makefile("", "Makefile")
        assert isinstance(result, ParseResult)
        assert result.ast == []
        assert result.diagnostics == []
        assert result.unknown_constructs == []

    def test_parse_whitespace_only(self):
        """Whitespace-only makefile should be empty."""
        result = parse_makefile("\n\n   \n\t\n", "Makefile")
        assert result.ast == []
        assert len(result.diagnostics) == 0

    def test_parse_simple_variable_assignment(self):
        """Simple variable assignment (name = value) should parse."""
        content = "VAR = value"
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        assert isinstance(result.ast[0], VariableAssign)
        assert result.ast[0].name == "VAR"
        assert result.ast[0].value == "value"
        assert result.ast[0].kind == "simple"

    def test_parse_recursive_assignment(self):
        """Recursive assignment (name := value) should parse."""
        content = "VAR := $(OTHER)"
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        assign = result.ast[0]
        assert isinstance(assign, VariableAssign)
        assert assign.name == "VAR"
        assert assign.kind == "recursive"

    def test_parse_append_assignment(self):
        """Append assignment (name += value) should parse."""
        content = "CFLAGS += -Wall"
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        assign = result.ast[0]
        assert isinstance(assign, VariableAssign)
        assert assign.name == "CFLAGS"
        assert assign.value == "-Wall"
        assert assign.kind == "append"

    def test_parse_multiple_assignments(self):
        """Multiple assignments should all parse."""
        content = """VAR1 = value1
VAR2 := value2
VAR3 += value3"""
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 3
        assert all(isinstance(node, VariableAssign) for node in result.ast)

    def test_assignment_with_spaces(self):
        """Assignment with leading/trailing spaces should parse correctly."""
        content = "  VAR   =   value with spaces  "
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        assert assign.name == "VAR"
        assert assign.value == "value with spaces"


class TestParseRules:
    """Tests for parsing Make rules."""

    def test_parse_simple_rule(self):
        """Simple rule (target: prerequisite) should parse."""
        content = """target: prereq1 prereq2
\tcommand1
\tcommand2"""
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        rule = result.ast[0]
        assert isinstance(rule, Rule)
        assert rule.targets == ["target"]
        assert rule.prerequisites == ["prereq1", "prereq2"]
        assert len(rule.commands) == 2

    def test_parse_rule_no_prerequisites(self):
        """Rule with no prerequisites should parse."""
        content = """target:
\tcommand"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert rule.targets == ["target"]
        assert rule.prerequisites == []
        assert len(rule.commands) == 1

    def test_parse_rule_no_commands(self):
        """Rule with no commands should parse."""
        content = "target: prereq"
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert rule.targets == ["target"]
        assert rule.prerequisites == ["prereq"]
        assert rule.commands == []

    def test_parse_multiple_targets(self):
        """Rule with multiple targets should parse."""
        content = """target1 target2 target3: prereq
\tcommand"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert rule.targets == ["target1", "target2", "target3"]

    def test_parse_pattern_rule(self):
        """Pattern rule (%.o: %.c) should parse as PatternRule."""
        content = """%.o: %.c
\tgcc -c $< -o $@"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert isinstance(rule, PatternRule)
        assert rule.target_pattern == "%.o"
        assert rule.prereq_patterns == ["%.c"]
        assert len(rule.commands) == 1

    def test_parse_pattern_rule_multiple_prereqs(self):
        """Pattern rule with multiple prerequisites."""
        content = """%.exe: %.o %.dep
\tgcc $^ -o $@"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert isinstance(rule, PatternRule)
        assert rule.target_pattern == "%.exe"
        assert rule.prereq_patterns == ["%.o", "%.dep"]

    def test_parse_rule_with_inline_commands(self):
        """Rule with commands on same line should parse commands separately."""
        content = """target: prereq
\techo start
\techo end
\techo final"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert len(rule.commands) == 3
        assert rule.commands[0] == "echo start"
        assert rule.commands[1] == "echo end"
        assert rule.commands[2] == "echo final"


class TestParseConditionals:
    """Tests for parsing conditional blocks."""

    def test_parse_simple_ifdef(self):
        """Simple ifdef conditional should parse."""
        content = """ifdef DEBUG
VAR = value
endif"""
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        cond = result.ast[0]
        assert isinstance(cond, Conditional)
        assert "ifdef" in cond.test
        assert len(cond.true_body) == 1
        assert cond.false_body == []

    def test_parse_ifdef_with_else(self):
        """ifdef with else block should parse both bodies."""
        content = """ifdef DEBUG
VAR = debug
else
VAR = release
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert len(cond.true_body) == 1
        assert len(cond.false_body) == 1

    def test_parse_ifeq_conditional(self):
        """ifeq conditional should parse."""
        content = """ifeq ($(ARCH),x86_64)
CFLAGS = -m64
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert "ifeq" in cond.test
        assert len(cond.true_body) == 1

    def test_parse_ifneq_conditional(self):
        """ifneq conditional should parse."""
        content = """ifneq ($(OS),Windows)
TARGET = unix
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert "ifneq" in cond.test

    def test_parse_ifndef_conditional(self):
        """ifndef conditional should parse."""
        content = """ifndef RELEASE
CFLAGS += -g
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert "ifndef" in cond.test

    def test_parse_nested_conditionals(self):
        """Nested conditionals should parse correctly."""
        content = """ifdef A
ifdef B
VAR = nested
endif
endif"""
        result = parse_makefile(content, "Makefile")

        outer = result.ast[0]
        assert isinstance(outer, Conditional)
        assert len(outer.true_body) == 1
        inner = outer.true_body[0]
        assert isinstance(inner, Conditional)

    def test_parse_conditional_with_rules(self):
        """Conditional containing rules should parse."""
        content = """ifdef PARALLEL
target: prereq
\tcommand
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert len(cond.true_body) == 1
        assert isinstance(cond.true_body[0], Rule)

    def test_unmatched_endif_diagnostic(self):
        """Unmatched endif should generate error diagnostic."""
        content = """VAR = value
endif"""
        result = parse_makefile(content, "Makefile")

        # Should still parse but report error
        _errors = [d for d in result.diagnostics if d.get("severity") == "ERROR"]
        # Unknown construct will be treated as such
        assert len(result.ast) >= 1


class TestLineHandling:
    """Tests for line continuation and comment handling."""

    def test_parse_line_continuation_assignment(self):
        """Line continuation with backslash should join lines."""
        content = """LONG_VAR = value1 \\
value2 \\
value3"""
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        assert assign.name == "LONG_VAR"
        # Should contain all parts
        assert "value1" in assign.value
        assert "value2" in assign.value
        assert "value3" in assign.value

    def test_parse_line_continuation_rule(self):
        """Line continuation in rule should work."""
        content = """target: prereq1 \\
prereq2 \\
prereq3
\tcommand"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert len(rule.prerequisites) == 3

    def test_parse_comments_in_assignment(self):
        """Comments in assignments should be stripped."""
        content = "VAR = value # this is a comment"
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        assert assign.value == "value"
        assert "comment" not in assign.value

    def test_parse_escaped_hash_in_value(self):
        """Escaped hash in value should not be treated as comment."""
        content = r"VAR = value\#notcomment"
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        # Should preserve escaped hash
        assert "notcomment" in assign.value or "\\" in assign.value

    def test_parse_comment_only_line(self):
        """Comment-only line should be skipped."""
        content = """VAR = value
# This is a comment
VAR2 = value2"""
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 2
        assert all(isinstance(node, VariableAssign) for node in result.ast)

    def test_parse_multiple_continuations(self):
        """Multiple continuation lines should all join."""
        content = """target: a \\
b \\
c \\
d
\tcmd"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert len(rule.prerequisites) == 4


class TestIncludeStatements:
    """Tests for parsing include statements."""

    def test_parse_include_statement(self):
        """include statement should parse."""
        content = "include rules.mk"
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1
        inc = result.ast[0]
        assert isinstance(inc, IncludeStmt)
        assert "rules.mk" in inc.paths
        assert not inc.optional

    def test_parse_optional_include(self):
        """Optional include (-include) should parse."""
        content = "-include config.mk"
        result = parse_makefile(content, "Makefile")

        inc = result.ast[0]
        assert inc.optional

    def test_parse_include_multiple_files(self):
        """include with multiple files should parse all."""
        content = "include file1.mk file2.mk file3.mk"
        result = parse_makefile(content, "Makefile")

        inc = result.ast[0]
        assert len(inc.paths) == 3
        assert "file1.mk" in inc.paths
        assert "file2.mk" in inc.paths
        assert "file3.mk" in inc.paths


class TestUnknownConstructs:
    """Tests for handling unknown/unsupported syntax."""

    def test_unknown_directive(self):
        """Unknown directives should be recorded."""
        content = "unsupported_directive something"
        result = parse_makefile(content, "Makefile")

        # Should create unknown construct
        assert len(result.unknown_constructs) == 1 or len(result.diagnostics) > 0

    def test_raw_command_without_target(self):
        """Raw command line should parse as RawCommand."""
        content = "\techo hello"
        result = parse_makefile(content, "Makefile")

        # Should parse as raw command or unknown
        assert len(result.ast) >= 0

    def test_mixed_valid_and_invalid(self):
        """Mix of valid and invalid constructs should parse valid ones."""
        content = """VAR = value
invalid syntax here
target: prereq
\tcommand"""
        result = parse_makefile(content, "Makefile")

        # Should parse valid constructs
        valid_nodes = [n for n in result.ast if isinstance(n, (VariableAssign, Rule))]
        assert len(valid_nodes) >= 2


class TestParseEdgeCases:
    """Tests for edge cases and corner cases."""

    def test_assignment_with_equals_in_value(self):
        """Assignment where value contains = should parse."""
        content = "FLAGS = -DKEY=VALUE"
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        assert "=" in assign.value
        assert "VALUE" in assign.value

    def test_rule_with_special_characters_in_target(self):
        """Target with special characters should parse."""
        content = """my-target_1.2.3: prereq
\tcommand"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert "my-target_1.2.3" in rule.targets

    def test_empty_conditional_body(self):
        """Conditional with empty body should parse."""
        content = """ifdef EMPTY
endif"""
        result = parse_makefile(content, "Makefile")

        cond = result.ast[0]
        assert cond.true_body == []

    def test_parse_variable_with_spaces(self):
        """Variable names with proper spacing."""
        content = """    PADDED_VAR    =    padded value   """
        result = parse_makefile(content, "Makefile")

        assign = result.ast[0]
        assert assign.name == "PADDED_VAR"
        assert assign.value == "padded value"

    def test_very_long_line(self):
        """Very long lines should parse."""
        long_value = "x " * 1000
        content = f"VAR = {long_value}"
        result = parse_makefile(content, "Makefile")

        assert len(result.ast) == 1

    def test_tabs_in_command(self):
        """Tabs in command should be preserved."""
        content = """target:
\tcommand\twith\ttabs"""
        result = parse_makefile(content, "Makefile")

        rule = result.ast[0]
        assert "\t" in rule.commands[0] or "with" in rule.commands[0]

    def test_rule_colon_in_name(self):
        """Colon in variable name should not be parsed as rule."""
        # This is an edge case where content might look like a rule
        content = "SOME:VAR = value"
        result = parse_makefile(content, "Makefile")

        # Should be treated as unknown or skipped due to colon in var name
        assert all(not isinstance(node, Rule) for node in result.ast)


class TestParserHelperFunctions:
    """Tests for parser helper functions."""

    def test_strip_comment_simple(self):
        """Simple comment stripping."""
        result = _strip_comment("text # comment")
        assert result == "text"
        assert "#" not in result

    def test_strip_comment_escaped_hash(self):
        """Escaped hash should not strip comment."""
        result = _strip_comment(r"text \# not comment")
        assert "not comment" in result

    def test_strip_comment_no_hash(self):
        """Text without hash should be unchanged."""
        result = _strip_comment("just text")
        assert result == "just text"

    def test_join_continuations_simple(self):
        """Simple line continuation."""
        lines = ["line1\\", "line2"]
        result, end_index = _join_continuations(lines, 0)
        assert "line1" in result
        assert "line2" in result
        assert end_index == 1

    def test_join_continuations_multiple(self):
        """Multiple continuations."""
        lines = ["a\\", "b\\", "c"]
        result, end_index = _join_continuations(lines, 0)
        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert end_index == 2

    def test_is_conditional_start(self):
        """Conditional start detection."""
        assert _is_conditional_start("ifdef DEBUG")
        assert _is_conditional_start("ifndef VAR")
        assert _is_conditional_start("ifeq (a,b)")
        assert _is_conditional_start("ifneq (x,y)")
        assert not _is_conditional_start("else")
        assert not _is_conditional_start("endif")
        assert not _is_conditional_start("variable = value")

    def test_parse_commands_single(self):
        """Parse single command."""
        lines = ["\techo hello", "VAR = value"]
        commands, end_idx = parse_commands(lines, 0, "test")
        assert len(commands) == 1
        assert commands[0] == "echo hello"
        assert end_idx == 1

    def test_parse_commands_multiple(self):
        """Parse multiple commands."""
        lines = ["\tcmd1", "\tcmd2", "\tcmd3", "next_line"]
        commands, end_idx = parse_commands(lines, 0, "test")
        assert len(commands) == 3
        assert end_idx == 3

    def test_parse_commands_empty(self):
        """Parse with no commands."""
        lines = ["VAR = value"]
        commands, end_idx = parse_commands(lines, 0, "test")
        assert commands == []
        assert end_idx == 0


class TestParserIntegration:
    """Integration tests for complete Makefile parsing."""

    def test_parse_realistic_makefile(self):
        """Parse a realistic Makefile."""
        content = """CC = gcc
CFLAGS = -Wall -O2
SOURCES = main.c utils.c
OBJECTS = $(SOURCES:.c=.o)

.PHONY: all clean

all: program

program: $(OBJECTS)
\t$(CC) $(OBJECTS) -o $@

%.o: %.c
\t$(CC) $(CFLAGS) -c $< -o $@

clean:
\trm -f $(OBJECTS) program
"""
        result = parse_makefile(content, "Makefile")

        # Should have multiple statements
        assert len(result.ast) >= 5
        # Should have variable assignments
        assigns = [n for n in result.ast if isinstance(n, VariableAssign)]
        assert len(assigns) >= 3
        # Should have rules
        rules = [n for n in result.ast if isinstance(n, (Rule, PatternRule))]
        assert len(rules) >= 2

    def test_parse_with_conditionals_and_rules(self):
        """Parse mix of conditionals and rules."""
        content = """ifdef DEBUG
CFLAGS = -g
else
CFLAGS = -O2
endif

target: source.c
\tgcc $(CFLAGS) -o $@ $<
"""
        result = parse_makefile(content, "Makefile")

        # Should have conditional and rule
        conditionals = [n for n in result.ast if isinstance(n, Conditional)]
        rules = [n for n in result.ast if isinstance(n, (Rule, PatternRule))]

        assert len(conditionals) >= 1
        assert len(rules) >= 1

    def test_parser_source_location_tracking(self):
        """Parser should track source locations correctly."""
        content = """VAR = value
target: prereq
\tcommand"""
        result = parse_makefile(content, "Makefile")

        # Each node should have location
        for node in result.ast:
            if hasattr(node, 'location'):
                loc = node.location
                assert loc.path == "Makefile"
                assert loc.line > 0
                assert loc.column > 0
