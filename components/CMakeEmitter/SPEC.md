<component_spec name="CMakeEmitter">
<package>gmake2cmake.cmake.emitter</package>
<purpose>Generate CMakeLists.txt content from IR with deterministic formatting; optionally write to filesystem; preserve unknown flags as pass-through; centralize project-global config and namespaced aliases; record unmappable constructs for reporting.</purpose>
<dependencies>
- FileSystemAdapter for writes when not dry-run.
- DiagnosticsReporter for write errors.</dependencies>
<data>
- class GeneratedFile: path(str abs posix), content(str).
</data>
<data>
- class EmitOptions: dry_run(bool), packaging(bool), namespace(str).</data>
</data>
<functions>
  <function name="emit" signature="emit(project: Project, output_dir: Path, *, options: EmitOptions, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> list[GeneratedFile]">
  - Renders root CMakeLists.txt and subdir files when targets distributed across directories (based on source paths); writes optional ProjectGlobalConfig.cmake when globals present.
  - Adds cmake_minimum_required(VERSION 3.20) and project() header with languages and namespace.
  - Generates install/export/package files when options.packaging True, including MyProjectConfig.cmake and version files with namespace.
  - Writes files (UTF-8) when dry_run=False; on write failure adds ERROR EMIT_WRITE_FAIL.</function>
  <function name="render_root" signature="render_root(project: Project, subdirs: list[str], *, options: EmitOptions, has_global_module: bool) -> str">
  - Generates headers, options, add_subdirectory entries; includes ProjectGlobalConfig.cmake when present; sets global init flags (CMAKE_C_FLAGS_INIT/CMAKE_CXX_FLAGS_INIT) and root include directories when required.</function>
  <function name="render_global_module" signature="render_global_module(project_config: ProjectGlobalConfig, namespace: str) -> str">
  - Emits centralized options/set cache for feature_toggles, global flags/defines/includes; avoids duplicating per-subdir use; may create INTERFACE target to propagate global includes/defines.</function>
  <function name="render_target" signature="render_target(target: Target, rel_dir: str, namespace: str) -> str">
  - Emits add_executable/add_library/custom_command/interface/imported plus associated target_sources, target_include_directories, target_compile_definitions, target_compile_options, target_link_libraries.
  - For internal libraries, emits ALIAS target `Namespace::Name` referring to physical target; link statements use aliases.
  - Unknown flags passed to target_compile_options; link options to target_link_options; usage requirements respect PUBLIC/PRIVATE/INTERFACE.
  - Unrenderable target types or options should emit UNKNOWN_CONSTRUCT (category toolchain_specific/other) with cmake_status not_generated/approximate plus Diagnostic EMIT_UNKNOWN_TYPE.</function>
  <function name="render_packaging" signature="render_packaging(project: Project, namespace: str) -> dict[str, str]">
  - Returns generated content for install/export blocks and Config/ConfigVersion files; ensures consistent namespace and target export name.</function>
  <function name="plan_file_layout" signature="plan_file_layout(project: Project, output_dir: Path) -> dict[str, list[Target]]">
  - Groups targets by directory relative to project root; ensures output_dir contains needed subfolders; deterministic ordering.</function>
</functions>
<contracts>
- No mutation of IR objects; output content idempotent (same IR -> same content).
- Paths in generated files must be relative to current CMakeLists.txt location.
- Must include diagnostics for unknown target types (ERROR EMIT_UNKNOWN_TYPE) without writing invalid CMake.
- Any unmappable construct must be captured as UnknownConstruct with context and suggested_action manual_review/manual_custom_command.
- Global config must be centralized in root/module; subdirs include module instead of duplicating.
- Namespaced aliases must always be emitted for internal libs; linking must prefer alias.
- Packaging outputs must include install/export blocks and Config files when enabled.
- On dry_run, no filesystem access performed.</contracts>
<testing>
- Generate executable and library targets with sources and includes.
- Subdirectory emission with target sources in nested folders.
- Dry-run returns GeneratedFile objects without writes.
- Pass-through of unmapped flags into compile options.
- Alias target emission and usage in link statements; imported/interface targets behavior.
- Packaging mode produces install/export/Config files with namespace.
- Global config module inclusion and init flag handling.
- Error when output_dir unwritable (simulate via fs adapter).
- Unknown/emitter-unmappable constructs recorded as UnknownConstruct with diagnostics.</testing>
</component_spec>
