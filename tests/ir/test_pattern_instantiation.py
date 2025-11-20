"""Tests for pattern rule instantiation."""

import tempfile
from pathlib import Path

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir.patterns import (
    _find_pattern_matches,
    _is_simple_pattern,
    _pattern_to_regex,
    detect_pattern_priority,
    instantiate_patterns,
)
from gmake2cmake.make.evaluator import EvaluatedCommand, EvaluatedRule
from gmake2cmake.make.parser import SourceLocation


class TestIsSimplePattern:
    """Tests for simple pattern detection."""

    def test_simple_c_pattern(self):
        """Test simple %.c to %.o pattern is recognized."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc -c $< -o $@", expanded="gcc -c source.c -o target.o", location=loc)
        rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)

        assert _is_simple_pattern(rule)

    def test_cpp_pattern(self):
        """Test C++ pattern is recognized."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="g++ -c $< -o $@", expanded="g++ -c source.cpp -o target.o", location=loc)
        rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.cpp"], commands=[cmd], is_pattern=True, location=loc)

        assert _is_simple_pattern(rule)

    def test_pattern_with_directory(self):
        """Test pattern with directory prefix is recognized."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc -c $< -o $@", expanded="gcc -c src/test.c -o obj/test.o", location=loc)
        rule = EvaluatedRule(targets=["obj/%.o"], prerequisites=["src/%.c"], commands=[cmd], is_pattern=True, location=loc)

        assert _is_simple_pattern(rule)

    def test_multiple_targets_not_simple(self):
        """Test pattern with multiple targets is not simple."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc -c $< -o $@", expanded="", location=loc)
        rule = EvaluatedRule(
            targets=["%.o", "%.d"],
            prerequisites=["%.c"],
            commands=[cmd],
            is_pattern=True,
            location=loc,
        )

        assert not _is_simple_pattern(rule)

    def test_multiple_prerequisites_not_simple(self):
        """Test pattern with multiple prerequisites is not simple."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc -c $<", expanded="", location=loc)
        rule = EvaluatedRule(
            targets=["%.o"],
            prerequisites=["%.c", "header.h"],
            commands=[cmd],
            is_pattern=True,
            location=loc,
        )

        assert not _is_simple_pattern(rule)

    def test_multiple_percent_not_simple(self):
        """Test pattern with multiple % is not simple."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc -c", expanded="", location=loc)
        rule = EvaluatedRule(
            targets=["%.%.o"],
            prerequisites=["%.%.c"],
            commands=[cmd],
            is_pattern=True,
            location=loc,
        )

        assert not _is_simple_pattern(rule)

    def test_no_percent_not_simple(self):
        """Test rule with no % is not a simple pattern."""
        loc = SourceLocation(path="Makefile", line=1, column=1)
        cmd = EvaluatedCommand(raw="gcc", expanded="", location=loc)
        rule = EvaluatedRule(targets=["output.o"], prerequisites=["input.c"], commands=[cmd], is_pattern=True, location=loc)

        assert not _is_simple_pattern(rule)


class TestPatternToRegex:
    """Tests for pattern to regex conversion."""

    def test_simple_extension_pattern(self):
        """Test converting simple extension pattern."""
        pattern = "%.c"
        regex = _pattern_to_regex(pattern)
        assert regex == r"^(.+)\.c$"

    def test_pattern_with_directory(self):
        """Test pattern with directory prefix."""
        pattern = "src/%.c"
        regex = _pattern_to_regex(pattern)
        assert regex == r"^src/(.+)\.c$"

    def test_pattern_multiple_percent(self):
        """Test pattern with multiple percent signs."""
        pattern = "%.%.c"
        regex = _pattern_to_regex(pattern)
        # Should still convert to valid regex (even if not useful)
        assert "(.+)" in regex


class TestFindPatternMatches:
    """Tests for finding pattern matches in filesystem."""

    def test_simple_c_files(self):
        """Test finding .c files matching pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create some C files
            (root / "main.c").write_text("")
            (root / "util.c").write_text("")
            (root / "test.h").write_text("")

            loc = SourceLocation(path="Makefile", line=1, column=1)
            cmd = EvaluatedCommand(raw="gcc -c", expanded="", location=loc)
            rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)

            diagnostics = DiagnosticCollector()
            matches = _find_pattern_matches(rule, root, diagnostics)

            assert len(matches) == 2
            sources = {m.source for m in matches}
            assert any("main.c" in s for s in sources)
            assert any("util.c" in s for s in sources)

    def test_nested_directories(self):
        """Test finding files in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create nested structure
            (root / "src").mkdir()
            (root / "src" / "a.c").write_text("")
            (root / "src" / "b.c").write_text("")
            (root / "include" / "header.h").mkdir(parents=True)

            loc = SourceLocation(path="Makefile", line=1, column=1)
            cmd = EvaluatedCommand(raw="gcc -c", expanded="", location=loc)
            rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)

            diagnostics = DiagnosticCollector()
            matches = _find_pattern_matches(rule, root, diagnostics)

            assert len(matches) == 2

    def test_no_matches(self):
        """Test pattern with no matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test.txt").write_text("")

            loc = SourceLocation(path="Makefile", line=1, column=1)
            cmd = EvaluatedCommand(raw="gcc -c", expanded="", location=loc)
            rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)

            diagnostics = DiagnosticCollector()
            matches = _find_pattern_matches(rule, root, diagnostics)

            assert len(matches) == 0


class TestInstantiatePatterns:
    """Tests for full pattern instantiation."""

    def test_instantiate_simple_pattern(self):
        """Test instantiating simple pattern rule."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.c").write_text("")
            (root / "b.c").write_text("")

            loc = SourceLocation(path="Makefile", line=1, column=1)
            cmd = EvaluatedCommand(raw="gcc -c $< -o $@", expanded="", location=loc)
            pattern_rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)

            diagnostics = DiagnosticCollector()
            result = instantiate_patterns([pattern_rule], root, diagnostics)

            assert len(result.instantiated_rules) == 2
            assert len(result.pattern_mappings) > 0
            # Check that rules are concrete (not pattern)
            for rule in result.instantiated_rules:
                if not rule.is_pattern:
                    assert "%" not in rule.targets[0]

    def test_mixed_pattern_and_regular_rules(self):
        """Test mixed pattern and regular rules are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test.c").write_text("")

            loc = SourceLocation(path="Makefile", line=1, column=1)
            cmd = EvaluatedCommand(raw="gcc", expanded="", location=loc)

            pattern_rule = EvaluatedRule(targets=["%.o"], prerequisites=["%.c"], commands=[cmd], is_pattern=True, location=loc)
            regular_rule = EvaluatedRule(
                targets=["myprogram"],
                prerequisites=["test.o"],
                commands=[cmd],
                is_pattern=False,
                location=loc,
            )

            diagnostics = DiagnosticCollector()
            result = instantiate_patterns([pattern_rule, regular_rule], root, diagnostics)

            # Should have 1 instantiated from pattern + 1 regular = 2 total
            assert len(result.instantiated_rules) >= 2


class TestDetectPatternPriority:
    """Tests for pattern priority detection."""

    def test_single_match(self):
        """Test detecting priority with single matching pattern."""
        patterns = ["%.c"]
        winner = detect_pattern_priority(patterns, "main.c")
        assert winner == "%.c"

    def test_multiple_matches_specificity(self):
        """Test specificity-based priority detection."""
        patterns = ["%.c", "%.cpp"]
        # Both match, but %.cpp is more specific for .cpp file
        winner = detect_pattern_priority(patterns, "test.cpp")
        assert winner == "%.cpp"

    def test_no_matches(self):
        """Test when no patterns match."""
        patterns = ["%.c"]
        winner = detect_pattern_priority(patterns, "file.txt")
        assert winner is None

    def test_equal_specificity_order_matters(self):
        """Test that order matters when specificity is equal."""
        patterns = ["%.c", "%.c"]
        winner = detect_pattern_priority(patterns, "test.c")
        # Should return first match
        assert winner == "%.c"
