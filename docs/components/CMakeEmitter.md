# CMakeEmitter

Turns the IR into human-readable, modern CMake layouts.

```
Project IR
  -> plan_file_layout (root + subdirs)
  -> render_global_module (if globals)    ---> include() from root
  -> render_root (headers, subdirs, globals, options)
  -> render_target(s) (physical + alias)  ---> link internal deps via Namespace::name
  -> render_packaging (optional install/export/Config)
```

- **Purpose**: Produce deterministic `CMakeLists.txt` hierarchy (root + subdirs), centralized global config module, and optional packaging artifacts. Support dry-run vs actual writes.
- **Inputs**: Project (targets, aliases, ProjectGlobalConfig), output_dir, `EmitOptions` (dry_run, packaging, namespace), fs adapter, diagnostics.
- **Outputs**: `GeneratedFile` list; writes files when not dry-run (root/subdir `CMakeLists.txt`, `ProjectGlobalConfig.cmake`, packaging files).
- **Behavior details**:
  - `plan_file_layout` groups targets by directory so subdirs only own relevant targets.
  - `render_global_module` emits feature toggles (`option`/`set CACHE`), global flags (via `CMAKE_*_FLAGS_INIT` or INTERFACE target), and global includes/defines without duplicating per subdir.
  - `render_root` adds `cmake_minimum_required` + `project()` (with languages/namespace), includes global module, and adds `add_subdirectory` entries.
  - `render_target` handles executable/library/custom/interface/imported targets; creates ALIAS `Namespace::Name` for internal libs; applies PUBLIC/PRIVATE/INTERFACE usage for includes/defines/options/link libs; passes through unknown flags into options.
  - `render_packaging` emits `install(TARGETS ... EXPORT ...)`, header installs, exports with namespace, and `MyProjectConfig.cmake` + version file for `find_package`.
  - Write failures or unknown target types raise diagnostics (ERROR).
- **Interactions**: Consumes IR from IRBuilder; uses `namespace`/`packaging` flags from CLI/ConfigManager; diagnostics go to DiagnosticsReporter; dry_run avoids fs calls.
- **Spec**: [components/CMakeEmitter/SPEC.md](../../components/CMakeEmitter/SPEC.md)
