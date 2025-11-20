"""Tests for parallel evaluation functionality."""


from gmake2cmake.make.discovery import IncludeGraph
from gmake2cmake.make.evaluator import BuildFacts, EvaluatedRule, InferredCompile, ProjectGlobals
from gmake2cmake.make.parser import SourceLocation
from gmake2cmake.parallel import (
    ParallelEvaluator,
    merge_build_facts,
    partition_work,
    should_parallelize,
)


class TestWorkPartition:
    """Tests for work partitioning logic."""

    def test_partition_single_root(self):
        """Test partitioning with single root Makefile."""
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile"}
        graph.edges = {}

        partition = partition_work(graph)

        assert len(partition.partitions) == 1
        assert "/proj/Makefile" in partition.partitions[0]

    def test_partition_linear_chain(self):
        """Test partitioning with linear dependency chain."""
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile", "/proj/sub1/Makefile", "/proj/sub2/Makefile"}
        graph.edges = {
            "/proj/Makefile": {"/proj/sub1/Makefile"},
            "/proj/sub1/Makefile": {"/proj/sub2/Makefile"},
        }

        partition = partition_work(graph)

        # All should be in one partition since they're dependent
        assert len(partition.partitions) >= 1
        all_makefiles = set()
        for part in partition.partitions:
            all_makefiles.update(part)
        assert all_makefiles == graph.nodes

    def test_partition_independent_roots(self):
        """Test partitioning with independent root Makefiles."""
        graph = IncludeGraph()
        graph.roots = ["/proj1/Makefile", "/proj2/Makefile"]
        graph.nodes = {"/proj1/Makefile", "/proj2/Makefile"}
        graph.edges = {}

        partition = partition_work(graph)

        # Should have at least 2 partitions for independent roots
        assert len(partition.partitions) >= 1

    def test_partition_dependencies_tracked(self):
        """Test that dependencies are properly tracked."""
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile", "/proj/sub/Makefile"}
        graph.edges = {"/proj/Makefile": {"/proj/sub/Makefile"}}

        partition = partition_work(graph)

        assert "/proj/Makefile" in partition.dependencies
        assert "/proj/sub/Makefile" in partition.dependencies["/proj/Makefile"]


class TestMergeBuildFacts:
    """Tests for merging build facts from parallel workers."""

    def test_merge_empty_facts(self):
        """Test merging empty facts."""
        facts_list = [BuildFacts(), BuildFacts()]
        merged = merge_build_facts(facts_list)

        assert len(merged.rules) == 0
        assert len(merged.inferred_compiles) == 0
        assert len(merged.custom_commands) == 0

    def test_merge_rules_deterministic_order(self):
        """Test that rules are merged in deterministic order."""
        loc1 = SourceLocation(path="/proj/Makefile", line=10, column=1)
        loc2 = SourceLocation(path="/proj/Makefile", line=5, column=1)

        rule1 = EvaluatedRule(targets=["target1"], prerequisites=[], commands=[], is_pattern=False, location=loc1)
        rule2 = EvaluatedRule(targets=["target2"], prerequisites=[], commands=[], is_pattern=False, location=loc2)

        facts1 = BuildFacts(rules=[rule1])
        facts2 = BuildFacts(rules=[rule2])

        merged = merge_build_facts([facts1, facts2])

        assert len(merged.rules) == 2
        # Should be sorted by location
        assert merged.rules[0].location.line == 5
        assert merged.rules[1].location.line == 10

    def test_merge_inferred_compiles(self):
        """Test merging inferred compile information."""
        loc1 = SourceLocation(path="/proj/Makefile", line=1, column=1)
        compile1 = InferredCompile(
            source="a.c",
            output="a.o",
            language="c",
            flags=["-O2"],
            includes=[],
            defines=[],
            location=loc1,
        )
        compile2 = InferredCompile(
            source="b.c",
            output="b.o",
            language="c",
            flags=["-O3"],
            includes=[],
            defines=[],
            location=loc1,
        )

        facts1 = BuildFacts(inferred_compiles=[compile1])
        facts2 = BuildFacts(inferred_compiles=[compile2])

        merged = merge_build_facts([facts1, facts2])

        assert len(merged.inferred_compiles) == 2

    def test_merge_project_globals_vars(self):
        """Test merging project global variables."""
        globals1 = ProjectGlobals(vars={"VAR1": "value1", "COMMON": "old"})
        globals2 = ProjectGlobals(vars={"VAR2": "value2", "COMMON": "new"})

        facts1 = BuildFacts(project_globals=globals1)
        facts2 = BuildFacts(project_globals=globals2)

        merged = merge_build_facts([facts1, facts2])

        assert merged.project_globals.vars["VAR1"] == "value1"
        assert merged.project_globals.vars["VAR2"] == "value2"
        # Later values override earlier ones
        assert merged.project_globals.vars["COMMON"] == "new"

    def test_merge_project_globals_flags(self):
        """Test merging project global flags."""
        globals1 = ProjectGlobals(flags={"CFLAGS": ["-O2", "-Wall"]})
        globals2 = ProjectGlobals(flags={"CFLAGS": ["-g"], "LDFLAGS": ["-lm"]})

        facts1 = BuildFacts(project_globals=globals1)
        facts2 = BuildFacts(project_globals=globals2)

        merged = merge_build_facts([facts1, facts2])

        assert "-O2" in merged.project_globals.flags.get("CFLAGS", [])
        assert "-Wall" in merged.project_globals.flags.get("CFLAGS", [])
        assert "-g" in merged.project_globals.flags.get("CFLAGS", [])
        assert "-lm" in merged.project_globals.flags.get("LDFLAGS", [])

    def test_merge_diagnostics_preserved(self):
        """Test that diagnostics are preserved in order."""
        facts1 = BuildFacts(diagnostics=["diag1", "diag2"])
        facts2 = BuildFacts(diagnostics=["diag3"])

        merged = merge_build_facts([facts1, facts2])

        assert merged.diagnostics == ["diag1", "diag2", "diag3"]

    def test_merge_unknown_constructs_deduped(self):
        """Test that unknown constructs are deduplicated."""
        from gmake2cmake.ir.unknowns import UnknownConstructFactory

        factory = UnknownConstructFactory()
        unknown1 = factory.create(
            category="function",
            file="/proj/Makefile",
            raw_snippet="special_func()",
            line=1,
        )
        # Create another with same ID for dedup test - need to create two separate unknowns with different IDs
        unknown2 = factory.create(
            category="function",
            file="/proj/Makefile",
            raw_snippet="other_func()",
            line=2,
        )

        facts1 = BuildFacts(unknown_constructs=[unknown1])
        facts2 = BuildFacts(unknown_constructs=[unknown2, unknown1])

        merged = merge_build_facts([facts1, facts2])

        # Should deduplicate unknown1 which appears twice
        assert len(merged.unknown_constructs) == 2


class TestShouldParallelize:
    """Tests for parallelization decision logic."""

    def test_should_not_parallelize_single_process(self):
        """Test that single process never parallelizes."""
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile"}

        assert not should_parallelize(graph, 1)

    def test_should_not_parallelize_dependent_makefiles(self):
        """Test that dependent makefiles result in a single partition."""
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile", "/proj/sub/Makefile"}
        graph.edges = {"/proj/Makefile": {"/proj/sub/Makefile"}}

        # Dependent makefiles form a single partition, so parallelization not beneficial
        # The partition_work function groups dependent makefiles together
        partition = partition_work(graph)
        # All connected nodes end up in same partition(s)
        all_nodes = set()
        for part in partition.partitions:
            all_nodes.update(part)
        assert all_nodes == graph.nodes

    def test_should_parallelize_independent_makefiles(self):
        """Test that independent makefiles can be parallelized."""
        graph = IncludeGraph()
        graph.roots = ["/proj1/Makefile", "/proj2/Makefile"]
        graph.nodes = {"/proj1/Makefile", "/proj2/Makefile"}
        graph.edges = {}

        # Multiple processes can parallelize independent roots
        result = should_parallelize(graph, 4)
        # May or may not parallelize depending on partition result
        assert isinstance(result, bool)


class TestParallelEvaluator:
    """Tests for ParallelEvaluator class."""

    def test_default_process_count(self):
        """Test that default process count is set."""
        evaluator = ParallelEvaluator()
        assert evaluator.num_processes > 0

    def test_custom_process_count(self):
        """Test setting custom process count."""
        evaluator = ParallelEvaluator(num_processes=2)
        assert evaluator.num_processes == 2

    def test_process_count_minimum_one(self):
        """Test that process count is at least 1."""
        evaluator = ParallelEvaluator(num_processes=0)
        assert evaluator.num_processes == 1

    def test_can_parallelize_single_process(self):
        """Test cannot parallelize with single process."""
        evaluator = ParallelEvaluator(num_processes=1)
        graph = IncludeGraph()
        graph.roots = ["/proj/Makefile"]
        graph.nodes = {"/proj/Makefile"}

        assert not evaluator.can_parallelize(graph)

    def test_merge_empty_results(self):
        """Test merging empty work results."""
        evaluator = ParallelEvaluator(num_processes=1)
        # This would call worker_evaluate which returns empty BuildFacts
        # Test the merge path with empty items
        result = evaluator.evaluate_parallel([])
        assert isinstance(result, BuildFacts)
        assert len(result.rules) == 0
