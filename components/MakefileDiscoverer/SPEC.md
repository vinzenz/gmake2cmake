<component_spec name="MakefileDiscoverer">
<package>gmake2cmake.make.discovery</package>
<purpose>Resolve entry Makefile, traverse includes/subdir directives, and provide ordered Makefile contents with dependency graph diagnostics.</purpose>
<dependencies>
- FileSystemAdapter for path operations and file reads.
- DiagnosticsReporter for missing/cycle alerts.
</dependencies>
<data>
- class IncludeGraph: nodes(set[str]), edges(dict[str, set[str]]), roots(list[str]), cycles(list[list[str]]).
- class MakefileContent: path(str posix abs), content(str), included_from(str|None).
</data>
<functions>
  <function name="resolve_entry" signature="resolve_entry(source_dir: Path, entry_makefile: str|None, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> Path|None">
  - Prefers explicit entry_makefile; else tries Makefile/makefile/GNUmakefile in source_dir.
  - Emits ERROR DISCOVERY_ENTRY_MISSING when not found; returns None.</function>
  <function name="scan_includes" signature="scan_includes(entry: Path, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> IncludeGraph">
  - Performs DFS reading files line by line; detects `include` and `-include` directives and subdir recursions (`$(MAKE) -C` patterns).
  - Normalizes resolved paths to abs posix; tracks edges parent->child.
  - Detects cycles; records cycles with full path list; adds ERROR DISCOVERY_CYCLE.</function>
  <function name="collect_contents" signature="collect_contents(graph: IncludeGraph, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> list[MakefileContent]">
  - Reads files in topological order (parents before children); if file missing and was optional include (-include), adds WARN; mandatory include -> ERROR.
  - Returns decoded UTF-8 text; retains included_from for traceability.</function>
  <function name="discover" signature="discover(source_dir: Path, entry_makefile: str|None, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> tuple[IncludeGraph, list[MakefileContent]]">
  - Convenience wrapper: resolve_entry -> scan_includes -> collect_contents; short-circuits on fatal diagnostics.</function>
</functions>
<contracts>
- No parsing of Make content beyond include detection; leaves body to MakefileParser.
- All paths absolute posix; duplicates in nodes collapsed.
- Must not throw exceptions for missing optional includes; uses diagnostics.
- Must run deterministically regardless of filesystem traversal order.</contracts>
<testing>
- Missing entry -> ERROR; cycle detection with 3-file loop.
- Optional include missing -> WARN; mandatory -> ERROR.
- Subdir traversal with relative paths resolved correctly.
- Large graph ordering stable and deterministic.</testing>
</component_spec>
