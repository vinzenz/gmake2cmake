<component_spec name="IRBuilder">
<package>gmake2cmake.ir.builder</package>
<purpose>Transform BuildFacts into normalized IR entities (Project, Target, SourceFile, CustomCommand) applying config mappings, validation, and deduplication.</purpose>
<dependencies>
- ConfigModel for target/flag mappings and ignores.
- DiagnosticsReporter for structural errors.</dependencies>
<data>
- class IRBuildResult: project(Project), diagnostics(list[Diagnostic]).
- class TargetSpecHint: optional mapping from config to influence type and names.
- class ProjectGlobalConfig: vars(dict[str,str]), flags(dict[str,list[str]] keyed by language/all), defines(list[str]), includes(list[str]), feature_toggles(dict[str,str|bool]), sources(list[str]).
</data>
<functions>
  <function name="build_project" signature="build_project(facts: BuildFacts, config: ConfigModel, diagnostics: DiagnosticCollector) -> IRBuildResult">
  - Creates Project with name from config.project_name or inferred from source_dir name (provided via config or args); version from config.version; namespace from config.namespace or sanitized project name.
  - Aggregates languages from inferred compiles; default to ['C'] when empty.
  - Builds ProjectGlobalConfig from facts.project_globals merged with config flag mappings and ignore rules.
  - Invokes build_targets and attaches diagnostics; ensures target name uniqueness or emits ERROR IR_DUP_TARGET.</function>
  <function name="build_targets" signature="build_targets(facts: BuildFacts, config: ConfigModel, diagnostics: DiagnosticCollector) -> list[Target]">
  - Groups InferredCompile entries by output artifact; maps to target types (executable if extension missing or .exe; static if .a; shared if .so/.dylib; object if .o); can emit INTERFACE targets for shared flag bundles and IMPORTED targets for prebuilt libs when classified as external-but-shipped.
  - Applies config.target_mappings to rename targets and override type/link libs/includes/defines/options/visibility.
  - Applies ConfigManager.apply_flag_mapping to compile/link options; collects unmapped flags into diagnostics WARN IR_UNMAPPED_FLAG.
  - Determines internal vs external libraries using rules: presence of build facts for artifact, location inside source tree, config.link_overrides; assigns physical names (e.g., myproject_libfoo) and alias namespaced targets (e.g., Project::foo) for internals; externals remain raw; imported targets use config overrides.</function>
  <function name="make_source_files" signature="make_source_files(compiles: list[InferredCompile]) -> list[SourceFile]">
  - Normalizes paths to posix relative to project root when possible; deduplicates identical source paths while merging flags.</function>
  <function name="build_project_global_config" signature="build_project_global_config(globals: ProjectGlobals, config: ConfigModel, diagnostics: DiagnosticCollector) -> ProjectGlobalConfig">
  - Normalizes include dirs/flags/defines; applies flag mappings; prunes ignored paths; tags feature_toggles for later CMake option/set emission.</function>
  <function name="attach_dependencies" signature="attach_dependencies(targets: list[Target], rules: list[EvaluatedRule]) -> None">
  - Uses prerequisites to build dependency graph; sets Target.deps with names matching artifacts; prefers namespaced aliases for internal libs; skips ignored paths.</function>
  <function name="validate_ir" signature="validate_ir(project: Project, diagnostics: DiagnosticCollector) -> None">
  - Ensures no missing source files unless ignored; ensures target deps refer to known targets (WARN IR_UNKNOWN_DEP); validates compile options per language (lightweight whitelist); ensures aliases unique; ensures interface/imported targets not assigned sources; warns when globals duplicated into targets.</function>
</functions>
<contracts>
- No file writes; all inputs pure data objects.
- Deterministic ordering: targets sorted by name; sources sorted by path.
- Diagnostics on unsupported constructs must not stop other targets being built.
- CustomCommand entries preserved in IR for emitter mapping.
- Internal libraries must carry alias namespaced targets; externals must not create aliases.</contracts>
<testing>
- Target type inference for .o/.a/.so and fallback.
- Target mapping rename and override merge behavior.
- Flag mapping and unmapped warnings generation.
- Dependency linking across rules and ignored paths.
- Validation detecting unknown deps and missing sources.
- Global config normalization and dedup across facts/config.
- Internal vs external classification and alias naming.
- Interface/imported targets reject sources and set correct visibility.</testing>
</component_spec>
