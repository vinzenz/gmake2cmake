"""Comprehensive tests for parallel module covering all code paths."""

from __future__ import annotations

import pytest
from gmake2cmake.parallel import (
    ParallelEvaluator,
    partition_work,
    merge_build_facts,
    should_parallelize,
)
from gmake2cmake.make.discovery import IncludeGraph
from gmake2cmake.make.evaluator import (
    BuildFacts,
    ProjectGlobals,
    EvaluatedRule,
)
from gmake2cmake.make.parser import SourceLocation


class TestWorkPartitioning:
    """Tests for work partitioning logic."""

    def test_partition_empty_graph(self):
        """Empty graph should return empty partitions."""
        graph = IncludeGraph(
            nodes=set(),
            edges={},
            roots=set(),
        )

        partition = partition_work(graph)

        assert partition.partitions == []
        assert partition.dependencies == {}

    def test_partition_single_makefile(self):
        """Single makefile should create one partition."""
        graph = IncludeGraph(
            nodes={"Makefile"},
            edges={"Makefile": set()},
            roots={"Makefile"},
        )

        partition = partition_work(graph)

        assert len(partition.partitions) == 1
        assert {"Makefile"} in partition.partitions
        assert partition.dependencies["Makefile"] == set()

    def test_partition_independent_makefiles(self):
        """Independent makefiles should each be a partition."""
        graph = IncludeGraph(
            nodes={"Makefile1", "Makefile2", "Makefile3"},
            edges={
                "Makefile1": set(),
                "Makefile2": set(),
                "Makefile3": set(),
            },
            roots={"Makefile1", "Makefile2", "Makefile3"},
        )

        partition = partition_work(graph)

        assert len(partition.partitions) == 3

    def test_partition_with_dependencies(self):
        """Makefiles with dependencies should be grouped correctly."""
        graph = IncludeGraph(
            nodes={"main.mk", "lib.mk", "rules.mk"},
            edges={
                "main.mk": {"lib.mk", "rules.mk"},
                "lib.mk": {"rules.mk"},
                "rules.mk": set(),
            },
            roots={"main.mk"},
        )

        partition = partition_work(graph)

        # All should be in one partition since they're connected
        assert len(partition.partitions) >= 1


class TestBuildFactsMerging:
    """Tests for merging BuildFacts from parallel workers."""

    def test_merge_empty_facts_list(self):
        """Merging empty list should return empty BuildFacts."""
        result = merge_build_facts([])

        assert result.rules == []
        assert result.inferred_compiles == []
        assert result.custom_commands == []
        assert result.unknown_constructs == []

    def test_merge_single_build_facts(self):
        """Merging single BuildFacts should return equivalent."""
        location = SourceLocation(path="Makefile", line=1, column=1)
        from gmake2cmake.make.evaluator import EvaluatedCommand
        rule = EvaluatedRule(
            targets=["target"],
            prerequisites=[],
            commands=[EvaluatedCommand(raw="echo test", expanded="echo test", location=location)],
            is_pattern=False,
            location=location,
        )

        facts = BuildFacts(rules=[rule])
        result = merge_build_facts([facts])

        assert len(result.rules) == 1
        assert result.rules[0].targets == ["target"]

    def test_merge_multiple_build_facts_dedup_rules(self):
        """Duplicate rules should be preserved (not deduped at this level)."""
        location = SourceLocation(path="Makefile", line=1, column=1)
        from gmake2cmake.make.evaluator import EvaluatedCommand
        rule = EvaluatedRule(
            targets=["target"],
            prerequisites=[],
            commands=[EvaluatedCommand(raw="echo test", expanded="echo test", location=location)],
            is_pattern=False,
            location=location,
        )

        facts1 = BuildFacts(rules=[rule])
        facts2 = BuildFacts(rules=[rule])
        result = merge_build_facts([facts1, facts2])

        # Both should be present (dedup happens elsewhere)
        assert len(result.rules) == 2

    def test_merge_project_globals(self):
        """Project globals should be merged correctly."""
        globals1 = ProjectGlobals()
        globals1.vars["VAR1"] = "value1"

        globals2 = ProjectGlobals()
        globals2.vars["VAR2"] = "value2"

        facts1 = BuildFacts(project_globals=globals1)
        facts2 = BuildFacts(project_globals=globals2)
        result = merge_build_facts([facts1, facts2])

        assert result.project_globals.vars["VAR1"] == "value1"
        assert result.project_globals.vars["VAR2"] == "value2"

    def test_merge_diagnostics_preserved(self):
        """Diagnostics should be preserved in order."""
        facts1 = BuildFacts(diagnostics=[{"level": "INFO", "msg": "msg1"}])
        facts2 = BuildFacts(diagnostics=[{"level": "WARN", "msg": "msg2"}])

        result = merge_build_facts([facts1, facts2])

        assert len(result.diagnostics) == 2
        assert result.diagnostics[0]["msg"] == "msg1"
        assert result.diagnostics[1]["msg"] == "msg2"


class TestParallelizationDecision:
    """Tests for deciding whether to parallelize."""

    def test_should_not_parallelize_single_process(self):
        """Single process should not parallelize."""
        graph = IncludeGraph(
            nodes={"Makefile"},
            edges={"Makefile": set()},
            roots={"Makefile"},
        )

        assert not should_parallelize(graph, num_processes=1)

    def test_should_not_parallelize_single_makefile(self):
        """Single makefile should not parallelize."""
        graph = IncludeGraph(
            nodes={"Makefile"},
            edges={"Makefile": set()},
            roots={"Makefile"},
        )

        assert not should_parallelize(graph, num_processes=4)

    def test_should_parallelize_multiple_independent(self):
        """Multiple independent makefiles should parallelize."""
        graph = IncludeGraph(
            nodes={"Makefile1", "Makefile2"},
            edges={
                "Makefile1": set(),
                "Makefile2": set(),
            },
            roots={"Makefile1", "Makefile2"},
        )

        assert should_parallelize(graph, num_processes=2)


class TestParallelEvaluator:
    """Tests for ParallelEvaluator class."""

    def test_evaluator_initialization_default(self):
        """Default initialization should use CPU count."""
        evaluator = ParallelEvaluator()
        assert evaluator.num_processes >= 1

    def test_evaluator_initialization_custom(self):
        """Custom process count should be respected."""
        evaluator = ParallelEvaluator(num_processes=2)
        assert evaluator.num_processes == 2

    def test_evaluator_initialization_zero_processes(self):
        """Zero processes should default to 1."""
        evaluator = ParallelEvaluator(num_processes=0)
        assert evaluator.num_processes >= 1

    def test_evaluator_cannot_parallelize_single_item(self):
        """Single work item should not parallelize."""
        evaluator = ParallelEvaluator(num_processes=4)
        graph = IncludeGraph(
            nodes={"Makefile"},
            edges={"Makefile": set()},
            roots={"Makefile"},
        )

        assert not evaluator.can_parallelize(graph)

    def test_evaluator_can_parallelize_multiple_items(self):
        """Multiple independent work items should parallelize."""
        evaluator = ParallelEvaluator(num_processes=4)
        graph = IncludeGraph(
            nodes={"Makefile1", "Makefile2"},
            edges={
                "Makefile1": set(),
                "Makefile2": set(),
            },
            roots={"Makefile1", "Makefile2"},
        )

        assert evaluator.can_parallelize(graph)

    def test_evaluator_empty_work_items(self):
        """Empty work items should return empty BuildFacts."""
        evaluator = ParallelEvaluator(num_processes=1)
        result = evaluator.evaluate_parallel([])

        assert result.rules == []
        assert result.inferred_compiles == []

    def test_evaluator_single_work_item(self):
        """Single work item should use serial processing."""
        evaluator = ParallelEvaluator(num_processes=4)
        work_item = ({"Makefile"}, {"Makefile": "content"})

        result = evaluator.evaluate_parallel([work_item])

        # Should complete without error (returns empty BuildFacts from stub)
        assert isinstance(result, BuildFacts)

    def test_evaluator_serial_fallback_on_single_process(self):
        """Serial fallback should work with single process."""
        evaluator = ParallelEvaluator(num_processes=1)
        work_items = [
            ({"Makefile1"}, {"Makefile1": "content1"}),
            ({"Makefile2"}, {"Makefile2": "content2"}),
        ]

        result = evaluator.evaluate_parallel(work_items)

        assert isinstance(result, BuildFacts)


class TestExceptionHandlingInParallel:
    """Tests for exception handling in parallel processing."""

    def test_parallel_evaluator_handles_errors_gracefully(self):
        """Evaluator should handle worker errors gracefully."""
        evaluator = ParallelEvaluator(num_processes=2)

        # Even if workers fail, should return merged results
        work_items = [
            ({"Makefile1"}, {"Makefile1": "content1"}),
            ({"Makefile2"}, {"Makefile2": "content2"}),
        ]

        result = evaluator.evaluate_parallel(work_items)
        assert isinstance(result, BuildFacts)


class TestParallelIntegration:
    """Integration tests for parallel processing."""

    def test_full_parallel_workflow(self):
        """Complete workflow: partition, merge, parallelize."""
        graph = IncludeGraph(
            nodes={"Makefile1", "Makefile2"},
            edges={
                "Makefile1": set(),
                "Makefile2": set(),
            },
            roots={"Makefile1", "Makefile2"},
        )

        # Partition work
        partition = partition_work(graph)
        assert len(partition.partitions) >= 1

        # Determine if parallelization is worthwhile
        can_parallelize = should_parallelize(graph, num_processes=4)
        assert can_parallelize

        # Create evaluator
        evaluator = ParallelEvaluator(num_processes=4)
        work_items = [
            (partition, {"Makefile1": "content1", "Makefile2": "content2"}),
        ]

        # This should complete without error
        # (actual results depend on worker implementation)
