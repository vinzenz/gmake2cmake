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
    template_candidates = ["Makefile.in", "Makefile.tpl", "Makefile.def"]
    found_templates: List[str] = []
    for name in template_candidates:
        candidate = (source_dir / name).resolve()
        if fs.exists(candidate) and fs.is_file(candidate):
            found_templates.append(candidate.as_posix())
    add(diagnostics, "ERROR", "DISCOVERY_ENTRY_MISSING", f"No Makefile found in {source_dir}")
    if found_templates:
        templates = ", ".join(found_templates)
        add(
            diagnostics,
            "WARN",
            "DISCOVERY_TEMPLATE_ENTRY",
            f"Template Makefiles found ({templates}) but no generated Makefile. Run ./configure or ./Configure to bootstrap, or pass --entry-makefile to use a template directly.",
            location=str(source_dir),
        )
    return None


def scan_includes(entry: Path, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> IncludeGraph:
    graph = IncludeGraph()
    graph.roots.append(entry.as_posix())
    visited_stack: List[str] = []
    optional_seen: Set[tuple[str, str]] = set()

    def _record_cycle(start_index: int) -> None:
        cycle_nodes = visited_stack[start_index:] + [visited_stack[start_index]]
        if cycle_nodes in graph.cycles:
            return
        graph.cycles.append(cycle_nodes)
        add(
            diagnostics,
            "ERROR",
            "DISCOVERY_CYCLE",
            f"Recursive make/include cycle: {' -> '.join(cycle_nodes)}",
            location=cycle_nodes[-1],
        )

    def dfs(path: Path) -> None:
        node = path.as_posix()
        if node in visited_stack:
            _record_cycle(visited_stack.index(node))
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
            if stripped.startswith(("include ", "-include ", "sinclude ")):
                optional = stripped.startswith(("-include", "sinclude"))
                parts = [token for token in stripped.split()[1:] if token]
                for inc in parts:
                    if inc.startswith("$(wildcard"):
                        continue
                    cleaned = inc.rstrip(":|")
                    if cleaned.startswith(("$(dep_files", "$(dep_files_present")):
                        continue
                    if cleaned.startswith(("arch/$", "config.mak", "config.mak.autogen")):
                        cleaned = cleaned.replace("$(ARCH)", "ARCH")
                    child = (path.parent / cleaned).resolve()
                    _record_edge(graph, node, child.as_posix())
                    if fs.exists(child):
                        dfs(child)
                        continue
                    if optional:
                        diag_key = (child.as_posix(), f"{path}:{line_no}")
                        if diag_key not in optional_seen:
                            add(
                                diagnostics,
                                "WARN",
                                "DISCOVERY_INCLUDE_OPTIONAL_MISSING",
                                f"Optional include missing {child}",
                                location=f"{path}:{line_no}",
                                line=str(line),
                            )
                            optional_seen.add(diag_key)
                    else:
                        add(
                            diagnostics,
                            "ERROR",
                            "DISCOVERY_INCLUDE_MISSING",
                            f"Missing include {child} from {path}",
                            location=f"{path}:{line_no}",
                            line=str(line),
                        )
            if "$(MAKE)" in stripped and " -C " in stripped:
                _handle_recursive_make(
                    stripped,
                    path,
                    line_no,
                    fs,
                    diagnostics,
                    graph,
                    node,
                    dfs,
                    _record_cycle,
                    visited_stack,
                )
        visited_stack.pop()

    dfs(entry)
    return graph


def _record_edge(graph: IncludeGraph, parent: str, child: str) -> None:
    graph.edges.setdefault(parent, set()).add(child)


def _normalize_recursive_dir(token: str) -> str:
    cleaned = token.split("#", 1)[0]  # strip inline comments
    cleaned = cleaned.replace("$(", "").replace(")", "").replace("${", "").replace("}", "")
    cleaned = cleaned.replace("$@", "").replace("$<", "").replace("$^", "")
    cleaned = cleaned.replace("$$", "")
    return cleaned.strip()


def _handle_recursive_make(
    stripped: str,
    path: Path,
    line_no: int,
    fs: FileSystemAdapter,
    diagnostics: DiagnosticCollector,
    graph: IncludeGraph,
    node: str,
    dfs_fn,
    record_cycle,
    visited_stack: List[str],
) -> None:
    try:
        dir_part = stripped.split("-C", 1)[1].strip().split()[0]
    except (IndexError, ValueError):
        return
    if not dir_part:
        return
    normalized_dir = _normalize_recursive_dir(dir_part)
    if not normalized_dir or normalized_dir.startswith(("#", "$")):
        return
    child_path = (path.parent / normalized_dir / "Makefile").resolve()
    child_node = child_path.as_posix()
    _record_edge(graph, node, child_node)
    if child_node in visited_stack:
        record_cycle(visited_stack.index(child_node))
        return
    if fs.exists(child_path):
        dfs_fn(child_path)
    else:
        add(
            diagnostics,
            "WARN",
            "DISCOVERY_SUBDIR_MISSING",
            f"Subdir Makefile missing at {child_path}",
            location=f"{path}:{line_no}",
            line=str(stripped),
        )


def collect_contents(graph: IncludeGraph, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> List[MakefileContent]:
    contents: List[MakefileContent] = []
    visited: Set[str] = set()
    invalid_nodes: Set[str] = set()
    seen_failures: Set[str] = set()

    def visit(node: str, parent: Optional[str]) -> None:
        if node in visited:
            return
        visited.add(node)
        if any(tok in node for tok in ["$(", "*", "|"]):
            invalid_nodes.add(node)
            return
        try:
            text = fs.read_text(Path(node))
            if len(text.encode("utf-8", errors="ignore")) > MAX_FILE_SIZE_BYTES:
                if node not in seen_failures:
                    add(
                        diagnostics,
                        "ERROR",
                        "DISCOVERY_READ_FAIL",
                        f"Failed to read {node}: exceeds size limit {MAX_FILE_SIZE_BYTES} bytes",
                        location=node,
                    )
                    seen_failures.add(node)
                return
        except (OSError, UnicodeDecodeError, KeyError) as exc:  # pragma: no cover - IO error
            if node not in seen_failures:
                add(
                    diagnostics,
                    "WARN",
                    "DISCOVERY_READ_FAIL",
                    f"Failed to read {node}: {exc}",
                    location=node,
                )
                seen_failures.add(node)
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
