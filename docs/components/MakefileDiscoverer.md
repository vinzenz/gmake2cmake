# MakefileDiscoverer

Finds the Makefile universe before parsing.

```
entry (Makefile/makefile/GNUmakefile or -f)
   \
    \-- DFS includes + $(MAKE) -C subdirs --> IncludeGraph
                                     \
                                      \-> ordered MakefileContent[]
```

- **Purpose**: Resolve the starting Makefile, walk includes and subdir invocations, and surface graph problems early.
- **Inputs**: `source_dir`, `entry_makefile` (from CLI), fs adapter, diagnostics.
- **Outputs**: `IncludeGraph` (nodes/edges/cycles) and ordered `MakefileContent` (path, text, included_from).
- **Behavior details**:
  - `resolve_entry` chooses explicit `-f` or falls back to Makefile/makefile/GNUmakefile.
  - `scan_includes` detects `include`/`-include` and `$(MAKE) -C` patterns, normalizes to absolute posix paths, tracks edges, flags cycles (ERROR).
  - `collect_contents` reads files in topo order; missing optional include → WARN; missing mandatory → ERROR.
- **Interactions**: Output feeds MakefileParser. Diagnostics bubble to CLIController/DiagnosticsReporter. No config-ignore logic here; evaluator handles ignores.
- **Spec**: [components/MakefileDiscoverer/SPEC.md](../../components/MakefileDiscoverer/SPEC.md)
