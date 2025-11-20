"""Cycle detection for target dependencies in IR builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.builder import Target


@dataclass
class DependencyCycle:
    """Represents a detected dependency cycle."""

    path: List[str] = field(default_factory=list)
    """Ordered list of target names forming the cycle."""

    @property
    def cycle_string(self) -> str:
        """Get human-readable cycle string."""
        if not self.path:
            return ""
        # Form cycle: A -> B -> C -> A
        cycle_str = " -> ".join(self.path)
        if self.path:
            cycle_str += f" -> {self.path[0]}"
        return cycle_str


@dataclass
class CycleDetectionResult:
    """Result of cycle detection."""

    cycles: List[DependencyCycle] = field(default_factory=list)
    has_cycles: bool = False
    affected_targets: Set[str] = field(default_factory=set)
    """Targets involved in any cycle."""


def detect_cycles(targets: List[Target], diagnostics: DiagnosticCollector) -> CycleDetectionResult:
    """Detect circular dependencies in target dependency graph.

    Uses DFS-based cycle detection with multiple root sources.
    Reports all found cycles, not just the first.

    Args:
        targets: List of targets with dependencies
        diagnostics: Diagnostic collector for error reporting

    Returns:
        CycleDetectionResult with all detected cycles
    """
    result = CycleDetectionResult()

    # Build adjacency list from targets
    dep_graph: Dict[str, Set[str]] = {}
    target_lookup: Dict[str, Target] = {}

    for target in targets:
        target_lookup[target.name] = target
        target_lookup[target.artifact] = target
        if target.alias:
            target_lookup[target.alias] = target

        dep_graph[target.name] = set(target.deps)

    # Use Tarjan's SCC algorithm to find all strongly connected components
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def tarjan_dfs(node: str, stack: List[str]) -> None:
        """DFS for Tarjan's SCC algorithm."""
        visited.add(node)
        rec_stack.add(node)
        stack.append(node)

        for neighbor in dep_graph.get(node, set()):
            if neighbor not in visited:
                tarjan_dfs(neighbor, stack)
            elif neighbor in rec_stack:
                # Found a back edge - extract cycle
                try:
                    cycle_start_idx = stack.index(neighbor)
                    cycle_path = stack[cycle_start_idx:] + [neighbor]
                    result.cycles.append(DependencyCycle(path=cycle_path))
                except ValueError:
                    pass

        if stack and stack[-1] == node:
            stack.pop()
            rec_stack.discard(node)

    # Run DFS from all unvisited nodes
    for node in dep_graph:
        if node not in visited:
            tarjan_dfs(node, [])

    # Simpler approach: run basic DFS from each node to detect back edges
    # This finds all cycles (not just SCCs)
    result.cycles.clear()  # Clear previous partial results
    visited.clear()
    rec_stack.clear()

    for start_node in dep_graph:
        if start_node in visited:
            continue

        def dfs_find_cycles(node: str, path: List[str]) -> None:
            """DFS that finds cycles by detecting back edges."""
            if node in rec_stack:
                # Found a cycle
                try:
                    cycle_start_idx = path.index(node)
                    cycle_path = path[cycle_start_idx:] + [node]
                    cycle = DependencyCycle(path=cycle_path[:-1])
                    # Avoid duplicate cycles
                    if not any(set(c.path) == set(cycle.path) for c in result.cycles):
                        result.cycles.append(cycle)
                except ValueError:
                    pass
                return

            if node in visited and node not in path:
                return

            rec_stack.add(node)
            path.append(node)

            for neighbor in dep_graph.get(node, set()):
                dfs_find_cycles(neighbor, path[:])

            path.pop()
            rec_stack.discard(node)

        dfs_find_cycles(start_node, [])
        visited.add(start_node)

    # Report findings
    if result.cycles:
        result.has_cycles = True
        for cycle in result.cycles:
            result.affected_targets.update(cycle.path)
            add(
                diagnostics,
                "ERROR",
                "IR_DEPENDENCY_CYCLE",
                f"Circular dependency detected: {cycle.cycle_string}",
            )

    return result


def break_cycles(targets: List[Target], cycles: List[DependencyCycle]) -> None:
    """Break circular dependencies by removing problematic edges.

    Removes the "last" dependency in each cycle to break the loop while
    preserving as many dependencies as possible.

    Args:
        targets: List of targets to modify
        cycles: List of detected cycles
    """
    if not cycles:
        return

    # For each cycle, remove one dependency to break it
    for cycle in cycles:
        if len(cycle.path) < 2:
            continue

        # Remove the edge from last element back to first
        from_target = cycle.path[-1]
        to_target = cycle.path[0]

        # Find and update the target
        for target in targets:
            if target.name == from_target and to_target in target.deps:
                target.deps.remove(to_target)
                break


def validate_no_cycles(targets: List[Target]) -> bool:
    """Check if targets have any circular dependencies.

    Args:
        targets: List of targets to check

    Returns:
        True if no cycles, False if cycles exist
    """
    dep_graph: Dict[str, Set[str]] = {}
    for target in targets:
        dep_graph[target.name] = set(target.deps)

    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def has_cycle(node: str) -> bool:
        """Check if there's a cycle from this node."""
        if node in rec_stack:
            return True
        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        for neighbor in dep_graph.get(node, set()):
            if has_cycle(neighbor):
                return True

        rec_stack.discard(node)
        return False

    for node in dep_graph:
        visited.clear()
        rec_stack.clear()
        if has_cycle(node):
            return False

    return True
