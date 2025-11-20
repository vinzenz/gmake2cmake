"""Multiprocessing support for parallel evaluation of independent Makefiles."""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gmake2cmake.make.discovery import IncludeGraph
from gmake2cmake.make.evaluator import BuildFacts, EvaluatedRule, InferredCompile


@dataclass
class WorkPartition:
    """A partition of work for parallel processing."""

    partitions: List[Set[str]] = field(default_factory=list)
    """Each element is a set of makefile paths that can be processed independently."""

    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    """For each path, set of paths it depends on (for deterministic ordering)."""


def partition_work(graph: IncludeGraph) -> WorkPartition:
    """Partition makefiles into independent chunks based on include dependencies.

    Args:
        graph: Include graph from discovery phase

    Returns:
        WorkPartition with independent chunks and dependency info
    """
    partition = WorkPartition()

    # Build reverse dependency map for efficient traversal
    reverse_deps: Dict[str, Set[str]] = {}
    for parent, children in graph.edges.items():
        for child in children:
            if child not in reverse_deps:
                reverse_deps[child] = set()
            reverse_deps[child].add(parent)

    visited: Set[str] = set()
    processed: Set[str] = set()

    def get_all_dependents(node: str, all_deps: Set[str]) -> None:
        """Recursively collect all nodes that depend on a given node."""
        if node in processed:
            return
        processed.add(node)
        all_deps.add(node)
        for dependent in reverse_deps.get(node, set()):
            if dependent not in all_deps:
                get_all_dependents(dependent, all_deps)

    # For each root, identify the strongly connected component
    for root in graph.roots:
        if root not in visited:
            # This root and all its dependents form a unit
            component: Set[str] = set()
            get_all_dependents(root, component)

            # Add direct dependencies from component
            for node in component:
                if node not in partition.dependencies:
                    partition.dependencies[node] = set()
                for dep in graph.edges.get(node, set()):
                    partition.dependencies[node].add(dep)

            partition.partitions.append(component)
            visited.update(component)

    # Add any remaining nodes
    for node in graph.nodes:
        if node not in visited:
            partition.partitions.append({node})
            partition.dependencies[node] = graph.edges.get(node, set())

    return partition


def merge_build_facts(fact_list: List[BuildFacts]) -> BuildFacts:
    """Merge multiple BuildFacts from parallel workers."""
    merged = BuildFacts()
    merged.rules = _merge_rules(fact_list)
    merged.inferred_compiles = _merge_inferred_compiles(fact_list)
    merged.custom_commands = _merge_custom_commands(fact_list)
    _merge_project_globals(fact_list, merged)
    _merge_diagnostics(fact_list, merged)
    merged.unknown_constructs = _merge_unknowns(fact_list)
    return merged


def _merge_rules(fact_list: List[BuildFacts]) -> List[EvaluatedRule]:
    all_rules: List[EvaluatedRule] = []
    for facts in fact_list:
        all_rules.extend(facts.rules)
    return sorted(all_rules, key=lambda r: (r.location.path, r.location.line, r.location.column))


def _merge_inferred_compiles(fact_list: List[BuildFacts]) -> List[InferredCompile]:
    all_compiles: List[InferredCompile] = []
    for facts in fact_list:
        all_compiles.extend(facts.inferred_compiles)
    return sorted(all_compiles, key=lambda c: (c.location.path, c.location.line, c.source))


def _merge_custom_commands(fact_list: List[BuildFacts]) -> List[EvaluatedRule]:
    all_custom: List[EvaluatedRule] = []
    for facts in fact_list:
        all_custom.extend(facts.custom_commands)
    return sorted(all_custom, key=lambda r: (r.location.path, r.location.line, r.location.column))


def _merge_project_globals(fact_list: List[BuildFacts], merged: BuildFacts) -> None:
    for facts in fact_list:
        for key, value in facts.project_globals.vars.items():
            merged.project_globals.vars[key] = value
        for key, flags in facts.project_globals.flags.items():
            if key not in merged.project_globals.flags:
                merged.project_globals.flags[key] = []
            merged.project_globals.flags[key].extend(flags)
        merged.project_globals.defines.extend(facts.project_globals.defines)
        merged.project_globals.includes.extend(facts.project_globals.includes)
        for key, value in facts.project_globals.feature_toggles.items():
            merged.project_globals.feature_toggles[key] = value
        merged.project_globals.sources.extend(facts.project_globals.sources)


def _merge_diagnostics(fact_list: List[BuildFacts], merged: BuildFacts) -> None:
    for facts in fact_list:
        merged.diagnostics.extend(facts.diagnostics)


def _merge_unknowns(fact_list: List[BuildFacts]) -> List:
    merged_unknowns: List = []
    seen_unknowns: Set[str] = set()
    for facts in fact_list:
        for unknown in facts.unknown_constructs:
            if unknown.id not in seen_unknowns:
                merged_unknowns.append(unknown)
                seen_unknowns.add(unknown.id)
    return merged_unknowns


def worker_evaluate(work_item: Tuple[Set[str], Dict[str, str]]) -> BuildFacts:
    """Worker function for evaluating a partition of makefiles.

    This runs in a separate process and must be pickle-able.

    Args:
        work_item: Tuple of (makefile_paths, makefile_contents)

    Returns:
        BuildFacts from evaluating this partition
    """
    # This is a placeholder - actual implementation depends on evaluator API
    # In a real implementation, this would receive makefiles and evaluate them
    return BuildFacts()


def should_parallelize(graph: IncludeGraph, num_processes: int) -> bool:
    """Determine if parallelization would be beneficial.

    Args:
        graph: Include graph
        num_processes: Number of processes to use

    Returns:
        True if parallelization is worth overhead
    """
    if num_processes <= 1:
        return False

    # Only parallelize if there are multiple independent makefiles
    partition = partition_work(graph)
    return len(partition.partitions) > 1


class ParallelEvaluator:
    """Parallel evaluator using multiprocessing.Pool for independent Makefiles.

    Handles work partitioning, worker management, and result merging
    with proper error handling and resource cleanup.
    """

    def __init__(self, num_processes: Optional[int] = None) -> None:
        """Initialize parallel evaluator.

        Args:
            num_processes: Number of worker processes (None = CPU count)
        """
        if num_processes is None:
            self.num_processes = mp.cpu_count()
        else:
            self.num_processes = max(1, num_processes)

    def can_parallelize(self, graph: IncludeGraph) -> bool:
        """Check if graph can be parallelized."""
        return should_parallelize(graph, self.num_processes)

    def evaluate_parallel(self, work_items: List[Tuple[Set[str], Dict[str, str]]]) -> BuildFacts:
        """Evaluate work items in parallel.

        Args:
            work_items: List of (makefile_paths, makefile_contents) tuples

        Returns:
            Merged BuildFacts from all workers
        """
        if self.num_processes <= 1 or len(work_items) <= 1:
            # Fall back to serial processing
            results = []
            for item in work_items:
                results.append(worker_evaluate(item))
            return merge_build_facts(results)

        # Use multiprocessing pool
        results = []
        try:
            with mp.Pool(processes=self.num_processes) as pool:
                results = pool.map(worker_evaluate, work_items, chunksize=1)
        except (OSError, RuntimeError, mp.ProcessError) as e:
            # Graceful degradation: fall back to serial processing on error
            # OSError: System errors during pool creation
            # RuntimeError: Pool context manager issues
            # ProcessError: Worker process failures
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Parallel processing failed, falling back to serial: %s",
                e,
                exc_info=True
            )
            results = []
            for item in work_items:
                try:
                    results.append(worker_evaluate(item))
                except (OSError, RuntimeError) as worker_error:
                    # Continue processing other items but log the error
                    logger.error(
                        "Worker failed on item, using empty BuildFacts: %s",
                        worker_error,
                        exc_info=True
                    )
                    results.append(BuildFacts())

        return merge_build_facts(results)
