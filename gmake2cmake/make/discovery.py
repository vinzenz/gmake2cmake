from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.fs import FileSystemAdapter
from gmake2cmake.security import MAX_FILE_SIZE_BYTES


@dataclass
class IncludeGraph:
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=dict)
    roots: List[str] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)


@dataclass
class MakefileContent:
    path: str
    content: str
    included_from: Optional[str] = None


def resolve_entry(source_dir: Path, entry_makefile: Optional[str], fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> Optional[Path]:
    candidates = [entry_makefile] if entry_makefile else ["Makefile", "makefile", "GNUmakefile"]
    for name in candidates:
        candidate = (source_dir / name).resolve()
        if fs.exists(candidate) and fs.is_file(candidate):
            return candidate
    add(diagnostics, "ERROR", "DISCOVERY_ENTRY_MISSING", f"No Makefile found in {source_dir}")
    return None


def scan_includes(entry: Path, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> IncludeGraph:
    graph = IncludeGraph()
    graph.roots.append(entry.as_posix())
    visited_stack: List[str] = []

    def dfs(path: Path) -> None:
        node = path.as_posix()
        if node in visited_stack:
            cycle_index = visited_stack.index(node)
            graph.cycles.append(visited_stack[cycle_index:] + [node])
            add(
                diagnostics,
                "ERROR",
                "DISCOVERY_CYCLE",
                f"Include cycle detected: {' -> '.join(graph.cycles[-1])}",
                location=node,
            )
            return
        visited_stack.append(node)
        graph.nodes.add(node)
        lines = []
        try:
            lines = fs.read_text(path).splitlines()
        except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover - IO error
            add(
                diagnostics,
                "ERROR",
                "DISCOVERY_READ_FAIL",
                f"Failed to read {path}: {exc}",
                location=node,
            )
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Check for include statements
            if stripped.startswith("include") or stripped.startswith("-include"):
                optional = stripped.startswith("-include")
                parts = stripped.split()[1:]
                for inc in parts:
                    child = (path.parent / inc).resolve()
                    _record_edge(graph, node, child.as_posix())
                    if fs.exists(child):
                        dfs(child)
                    elif not optional:
                        add(
                            diagnostics,
                            "ERROR",
                            "DISCOVERY_INCLUDE_MISSING",
                            f"Missing include {child} from {path}",
                            location=f"{path}:{line_no}",
                        )
                    else:
                        add(
                            diagnostics,
                            "WARN",
                            "DISCOVERY_INCLUDE_OPTIONAL_MISSING",
                            f"Optional include missing {child}",
                            location=f"{path}:{line_no}",
                        )
            # Check for recursive make patterns $(MAKE) -C subdir
            if "$(MAKE)" in stripped and " -C " in stripped:
                # Extract directory after -C flag
                try:
                    dir_part = stripped.split("-C", 1)[1].strip().split()[0]
                    # Remove variable references if present (e.g., $(VAR) becomes VAR)
                    dir_part = dir_part.replace("$(", "").replace(")", "").replace("${", "").replace("}", "")
                    child_path = (path.parent / dir_part / "Makefile").resolve()
                    _record_edge(graph, node, child_path.as_posix())
                    if fs.exists(child_path):
                        dfs(child_path)
                    else:
                        add(
                            diagnostics,
                            "WARN",
                            "DISCOVERY_SUBDIR_MISSING",
                            f"Subdir Makefile missing at {child_path}",
                            location=f"{path}:{line_no}",
                        )
                except (IndexError, ValueError):
                    # Ignore malformed -C directives that cannot be parsed
                    pass
        visited_stack.pop()

    dfs(entry)
    return graph


def _record_edge(graph: IncludeGraph, parent: str, child: str) -> None:
    graph.edges.setdefault(parent, set()).add(child)


def collect_contents(graph: IncludeGraph, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> List[MakefileContent]:
    contents: List[MakefileContent] = []
    visited: Set[str] = set()

    def visit(node: str, parent: Optional[str]) -> None:
        if node in visited:
            return
        visited.add(node)
        try:
            text = fs.read_text(Path(node))
            if len(text.encode("utf-8", errors="ignore")) > MAX_FILE_SIZE_BYTES:
                add(
                    diagnostics,
                    "ERROR",
                    "DISCOVERY_READ_FAIL",
                    f"Failed to read {node}: exceeds size limit {MAX_FILE_SIZE_BYTES} bytes",
                    location=node,
                )
                return
        except (OSError, UnicodeDecodeError, KeyError) as exc:  # pragma: no cover - IO error
            add(
                diagnostics,
                "ERROR",
                "DISCOVERY_READ_FAIL",
                f"Failed to read {node}: {exc}",
                location=node,
            )
            return
        contents.append(MakefileContent(path=node, content=text, included_from=parent))
        for child in sorted(graph.edges.get(node, set())):
            visit(child, node)

    for root in graph.roots:
        visit(root, None)
    return contents


def discover(
    source_dir: Path,
    entry_makefile: Optional[str],
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
) -> tuple[IncludeGraph, list[MakefileContent]]:
    entry = resolve_entry(source_dir, entry_makefile, fs, diagnostics)
    if entry is None:
        return IncludeGraph(), []
    graph = scan_includes(entry, fs, diagnostics)
    contents = collect_contents(graph, fs, diagnostics) if not graph.cycles else []
    return graph, contents
