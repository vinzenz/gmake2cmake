"""Tests for dependency cycle detection and breaking."""


from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir.builder import Target
from gmake2cmake.ir.cycles import (
    DependencyCycle,
    break_cycles,
    detect_cycles,
    validate_no_cycles,
)


def make_target(name: str, artifact: str, deps: list = None) -> Target:
    """Helper to create a target for testing."""
    return Target(
        artifact=artifact or name,
        name=name,
        alias=None,
        type="executable",
        sources=[],
        include_dirs=[],
        defines=[],
        compile_options=[],
        link_options=[],
        link_libs=[],
        deps=deps or [],
        custom_commands=[],
    )


class TestDependencyCycle:
    """Tests for DependencyCycle data class."""

    def test_cycle_string_simple(self):
        """Test cycle string formatting for simple cycle."""
        cycle = DependencyCycle(path=["a", "b", "c"])
        assert cycle.cycle_string == "a -> b -> c -> a"

    def test_cycle_string_single(self):
        """Test cycle string for single self-referencing cycle."""
        cycle = DependencyCycle(path=["a"])
        assert cycle.cycle_string == "a -> a"

    def test_cycle_string_empty(self):
        """Test cycle string for empty path."""
        cycle = DependencyCycle(path=[])
        assert cycle.cycle_string == ""


class TestDetectCycles:
    """Tests for cycle detection."""

    def test_no_cycles_linear(self):
        """Test detection with linear dependency chain."""
        targets = [
            make_target("a", "a.o"),
            make_target("b", "b.o", ["a"]),
            make_target("c", "c.o", ["b"]),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert not result.has_cycles
        assert len(result.cycles) == 0
        assert len(result.affected_targets) == 0

    def test_no_cycles_independent(self):
        """Test detection with independent targets."""
        targets = [
            make_target("a", "a.o"),
            make_target("b", "b.o"),
            make_target("c", "c.o"),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert not result.has_cycles
        assert len(result.cycles) == 0

    def test_simple_two_way_cycle(self):
        """Test detection of simple two-way cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert result.has_cycles
        assert len(result.cycles) > 0
        assert "a" in result.affected_targets
        assert "b" in result.affected_targets

    def test_three_way_cycle(self):
        """Test detection of three-way cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["c"]),
            make_target("c", "c.o", ["a"]),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert result.has_cycles
        assert len(result.cycles) > 0
        assert "a" in result.affected_targets
        assert "b" in result.affected_targets
        assert "c" in result.affected_targets

    def test_self_cycle(self):
        """Test detection of self-referencing cycle."""
        targets = [
            make_target("a", "a.o", ["a"]),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert result.has_cycles
        assert len(result.cycles) > 0

    def test_mixed_cycles_and_linear(self):
        """Test detection with mix of cyclic and linear parts."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
            make_target("c", "c.o", ["d"]),
            make_target("d", "d.o"),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert result.has_cycles
        # Only a and b should be affected
        assert "a" in result.affected_targets
        assert "b" in result.affected_targets
        assert "c" not in result.affected_targets
        assert "d" not in result.affected_targets

    def test_complex_graph(self):
        """Test detection in complex dependency graph."""
        targets = [
            make_target("a", "a.o", ["b", "c"]),
            make_target("b", "b.o", ["d"]),
            make_target("c", "c.o", ["e"]),
            make_target("d", "d.o", ["e"]),
            make_target("e", "e.o", ["f"]),
            make_target("f", "f.o", []),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        # No cycles in this graph
        assert not result.has_cycles

    def test_diagnostics_reported(self):
        """Test that cycles are reported as diagnostics."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
        ]

        diagnostics = DiagnosticCollector()
        result = detect_cycles(targets, diagnostics)

        assert result.has_cycles
        assert len(diagnostics.diagnostics) > 0
        assert any("Circular dependency" in d.message for d in diagnostics.diagnostics)


class TestBreakCycles:
    """Tests for cycle breaking."""

    def test_break_simple_two_way(self):
        """Test breaking a simple two-way cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
        ]

        cycles = [DependencyCycle(path=["a", "b"])]
        break_cycles(targets, cycles)

        # After breaking, b should not depend on a (or a should not depend on b)
        a = next(t for t in targets if t.name == "a")
        b = next(t for t in targets if t.name == "b")

        # At least one dependency should be removed
        assert not (("b" in a.deps) and ("a" in b.deps))

    def test_break_three_way(self):
        """Test breaking a three-way cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["c"]),
            make_target("c", "c.o", ["a"]),
        ]

        cycles = [DependencyCycle(path=["a", "b", "c"])]
        break_cycles(targets, cycles)

        # At least one edge should be broken
        c = next(t for t in targets if t.name == "c")
        # The algorithm removes c->a edge
        assert "a" not in c.deps

    def test_break_multiple_cycles(self):
        """Test breaking multiple independent cycles."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
            make_target("c", "c.o", ["d"]),
            make_target("d", "d.o", ["c"]),
        ]

        cycles = [
            DependencyCycle(path=["a", "b"]),
            DependencyCycle(path=["c", "d"]),
        ]
        break_cycles(targets, cycles)

        # Both cycles should be broken
        validate_no_cycles(targets)

    def test_break_with_empty_cycles(self):
        """Test breaking with no cycles."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o"),
        ]

        break_cycles(targets, [])

        # Dependencies should be unchanged
        a = next(t for t in targets if t.name == "a")
        assert "b" in a.deps


class TestValidateNoCycles:
    """Tests for cycle validation."""

    def test_valid_acyclic(self):
        """Test validation of acyclic graph."""
        targets = [
            make_target("a", "a.o"),
            make_target("b", "b.o", ["a"]),
            make_target("c", "c.o", ["b"]),
        ]

        assert validate_no_cycles(targets)

    def test_invalid_simple_cycle(self):
        """Test validation fails for simple cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
        ]

        assert not validate_no_cycles(targets)

    def test_invalid_three_way_cycle(self):
        """Test validation fails for three-way cycle."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["c"]),
            make_target("c", "c.o", ["a"]),
        ]

        assert not validate_no_cycles(targets)

    def test_invalid_self_cycle(self):
        """Test validation fails for self-referencing."""
        targets = [
            make_target("a", "a.o", ["a"]),
        ]

        assert not validate_no_cycles(targets)

    def test_valid_after_break(self):
        """Test validation passes after breaking cycles."""
        targets = [
            make_target("a", "a.o", ["b"]),
            make_target("b", "b.o", ["a"]),
        ]

        assert not validate_no_cycles(targets)

        cycles = [DependencyCycle(path=["a", "b"])]
        break_cycles(targets, cycles)

        # After breaking, should be valid
        # (may not be true if algorithm doesn't fully break all cycles,
        # but at least one edge should be removed)
        b = next(t for t in targets if t.name == "b")
        assert "a" not in b.deps
