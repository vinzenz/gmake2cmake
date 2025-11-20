"""Deterministic ordering utilities for stable sorting across components."""

from __future__ import annotations

import re
from typing import Any, Callable, List, Optional, Set, TypeVar

T = TypeVar("T")


def stable_sort(items: List[T], key: Optional[Callable[[T], Any]] = None) -> List[T]:
    """Sort items stably, maintaining original order for equal keys.

    Args:
        items: List of items to sort.
        key: Optional key function for comparison.

    Returns:
        Sorted list with stable ordering preserved.
    """
    return sorted(items, key=key or (lambda x: x))


def topological_sort(graph: dict[str, Set[str]], nodes: Optional[Set[str]] = None) -> List[str]:
    """Perform topological sort on a directed acyclic graph.

    Handles partial orders and detects cycles.

    Args:
        graph: Dictionary mapping node -> set of dependencies.
        nodes: Optional set of all nodes. If None, will infer from graph.

    Returns:
        Topologically sorted list of nodes.

    Raises:
        ValueError: If a cycle is detected in the graph.
    """
    if nodes is None:
        nodes = set(graph.keys())
        for deps in graph.values():
            nodes.update(deps)

    # Create a copy of the graph to avoid modifying the original
    in_degree = {node: 0 for node in nodes}
    adj_list: dict[str, Set[str]] = {node: set() for node in nodes}

    for node, deps in graph.items():
        for dep in deps:
            if dep in nodes:
                adj_list[dep].add(node)
                in_degree[node] += 1

    # Kahn's algorithm with stable ordering
    queue = sorted([node for node in nodes if in_degree[node] == 0])
    result = []

    while queue:
        # Always process in sorted order for deterministic output
        queue.sort()
        node = queue.pop(0)
        result.append(node)

        for neighbor in sorted(adj_list[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(nodes):
        raise ValueError("Cycle detected in dependency graph")

    return result


def natural_sort(items: List[str], key: Optional[Callable[[str], str]] = None) -> List[str]:
    """Sort strings with natural (human-friendly) ordering.

    Handles mixed numeric and alphabetic content, e.g., file1, file10, file2
    sorts as: file1, file2, file10.

    Args:
        items: List of strings to sort.
        key: Optional key function to extract sortable string from item.

    Returns:
        Naturally sorted list.
    """

    def natural_key(text: str) -> List[Any]:
        """Convert string to list for natural sorting."""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]

    if key:
        return sorted(items, key=lambda x: natural_key(key(x)))
    return sorted(items, key=natural_key)


def dependency_sort(items: List[T], dep_graph: dict[T, Set[T]]) -> List[T]:
    """Sort items respecting build order/dependency constraints.

    Args:
        items: List of items to sort.
        dep_graph: Dictionary mapping item -> set of items it depends on.

    Returns:
        Sorted list respecting dependencies.

    Raises:
        ValueError: If a cycle is detected in dependencies.
    """
    # Convert items to strings for the topological sort
    str_items = {i: str(item) for i, item in enumerate(items)}
    str_graph = {
        str_items[i]: {str_items[j] for j in range(len(items)) if items[j] in dep_graph.get(item, set())}
        for i, item in enumerate(items)
    }

    try:
        sorted_strs = topological_sort(str_graph, set(str_items.values()))
    except ValueError as e:
        raise ValueError(f"Circular dependency detected: {e}") from e

    # Map back to original items
    reverse_map = {v: items[k] for k, v in str_items.items()}
    return [reverse_map[s] for s in sorted_strs]


def sort_targets(targets: List[Any], key: Callable[[Any], str] = lambda t: t.name) -> List[Any]:
    """Sort targets deterministically by name.

    Args:
        targets: List of target objects.
        key: Function to extract sort key from target.

    Returns:
        Sorted target list.
    """
    return stable_sort(targets, key=key)


def sort_diagnostics(
    diagnostics: List[Any], severity_order: Optional[dict[str, int]] = None
) -> List[Any]:
    """Sort diagnostics with deterministic ordering.

    Args:
        diagnostics: List of diagnostic objects.
        severity_order: Optional mapping of severity to sort order.

    Returns:
        Sorted diagnostic list.
    """
    if severity_order is None:
        severity_order = {"ERROR": 0, "WARN": 1, "INFO": 2}

    def diag_key(d: Any) -> tuple:
        return (severity_order.get(d.severity, 99), d.code, d.message)

    return stable_sort(diagnostics, key=diag_key)


def sort_files(files: List[str]) -> List[str]:
    """Sort file paths with natural ordering.

    Args:
        files: List of file paths.

    Returns:
        Naturally sorted file paths.
    """
    return natural_sort(files)
