<architecture_doc>
<product>gmake2cmake: CLI that ingests GNU Make projects (single/recursive), builds an internal IR, and emits modern CMakeLists.txt with diagnostics and reports. Primary language: Python 3.11+. All code linted (ruff/flake8 equivalent) and tested (pytest) with unit+integration coverage.</product>
<runtime>
- Inputs: Makefiles (default or -f override), source tree, optional YAML config, flags (--source-dir, --entry-makefile, --output-dir, --config, --dry-run, --report, --with-packaging).
- Outputs: Generated CMakeLists.txt files (root + optional subdirs), console diagnostics, optional JSON diagnostics report.
- Non-functional: Medium projects complete in seconds/minutes; use caching and optional multiprocessing in evaluators; deterministic outputs; no network I/O during conversion.
</runtime>
<standards>
- Python packaging under `gmake2cmake` namespace; pure functions where feasible; side effects (I/O, logging) isolated.
- Logging via structured messages; diagnostics severities INFO/WARN/ERROR.
- Strict input validation; fail fast on malformed config unless `--ignore-errors` (future flag placeholder handled by ConfigManager).
- TDD-first: specs map 1:1 to tests; all public contracts documented with types; lint + pytest required in CI; integration tests run against scenario fixtures.
</standards>
<components>
- CLIController (`gmake2cmake.cli`): Parses arguments, wires components, coordinates run lifecycle, handles dry-run vs write.
- ConfigManager (`gmake2cmake.config`): Loads/validates YAML config, merges CLI defaults, exposes mappings and ignores.
- MakefileDiscoverer (`gmake2cmake.make.discovery`): Resolves entry Makefile, traverses includes/subdir DAG, normalizes paths, detects cycles.
- MakefileParser (`gmake2cmake.make.parser`): Parses Makefiles into AST tokens covering variables, rules, pattern rules, includes, conditionals.
- MakeEvaluator (`gmake2cmake.make.evaluator`): Evaluates variables/functions/autovars, expands rules, infers compiler invocations and artifacts, extracts project-global configs.
- IRBuilder (`gmake2cmake.ir.builder`): Converts evaluated make data into IR (Project, Targets, SourceFiles, GlobalConfig, Diagnostics, UnknownConstructs) applying config mappings and linking rules.
- CMakeEmitter (`gmake2cmake.cmake.emitter`): Generates CMakeLists.txt hierarchy (root + subdirs + optional global module), mapping targets and flags, emitting namespaced aliases and packaging outputs, preserving unknown flags and recording unmappable constructs.
- DiagnosticsReporter (`gmake2cmake.diagnostics`): Collects events across pipeline, deduplicates, renders console/JSON/Markdown summaries including unknown construct signals.
</components>
<data_model>
- Project: name (str), version (optional str), language(s) (set), targets (list[Target]), project_config(ProjectGlobalConfig), diagnostics (list[Diagnostic]), unknown_constructs (list[UnknownConstruct]).
- ProjectGlobalConfig: global_vars(dict[str,str]), global_flags(dict[str,list[str]] for c/cxx/asm/link), global_defines(list[str]), global_includes(list[str]), feature_toggles(dict[str,bool|str] for option/set cache), source_paths(list[str] for config files).
- Target: name (str physical), alias(str namespaced alias `Project::Name`|None), type (enum: executable/shared/static/object/custom/interface/imported), sources (list[SourceFile]), include_dirs (list[str]), defines (list[str]), compile_options (list[str]), link_options (list[str]), link_libs (list[str]), deps (list[str]), usage_visibility(enum PUBLIC/PRIVATE/INTERFACE per property), custom_commands (list[CustomCommand]).
- SourceFile: path (str, normalized, posix-like), language (enum: c/cpp/asm/other), flags (list[str]).
- CustomCommand: command (list[str]), outputs (list[str]), inputs (list[str]), working_dir (str|None).
- Diagnostic: severity (INFO/WARN/ERROR), message (str), location (path:line|None), code (str).
- UnknownConstruct: id (stable UCxxxx), category(make_syntax/make_function/shell_command/conditional_logic/toolchain_specific/other), file, line/column(optional), raw_snippet(trimmed), normalized_form(best-effort structural summary), context(targets, variables_in_scope, includes_stack), impact(phase=parse|evaluate|build_graph|cmake_generation, severity=info|warning|error), cmake_status(not_generated/partially_generated/approximate), suggested_action(manual_review/manual_custom_command/requires_mapping).
</data_model>
<flow>
1) CLIController reads args -> ConfigManager loads YAML -> merged settings.
2) MakefileDiscoverer builds include/subdir graph; yields ordered file list with dependency edges; emits diagnostics on cycles/missing files.
3) MakefileParser converts each file into AST nodes; references include directives for resolver; captures conditional branches symbolically.
4) MakeEvaluator resolves AST with variable environment + config overrides; expands pattern rules; infers compilation commands; identifies project-global config files/variables (e.g., config.mk/rules.mk/defs.mk and top-level var blocks); produces raw build facts (targets, sources, flags, commands, globals) + diagnostics/UnknownConstruct entries for unsupported functions or conditionals.
5) IRBuilder normalizes build facts into IR; applies config mappings for targets/flags/ignores; constructs ProjectGlobalConfig from discovered globals and ConfigModel overrides; infers internal vs external libs; attaches namespaced aliases; aggregates UnknownConstructs into Project; validates IR invariants (unique target names, paths exist where required unless ignored).
6) CMakeEmitter renders IR to CMake files respecting output-dir; centralizes ProjectGlobalConfig into root CMakeLists.txt and optional ProjectGlobalConfig.cmake module; emits namespaced ALIAS targets (`Project::Name`) for internal libs; maps linkages to namespaced targets vs raw libs; supports interface/imported targets; optional packaging mode emits install/export rules and MyProjectConfig.cmake; supports dry-run (returns content only) vs write (persist files); ensures cmake_minimum_required + project() header; unknown flags passed through in target options; unmappable constructs record UnknownConstruct (toolchain_specific/other) without hard-failing unless severity=ERROR.
7) DiagnosticsReporter aggregates diagnostics from all stages; prints console summary (including count of unknown constructs); when --report is set writes JSON report to output-dir/report.json containing diagnostics and unknown_constructs plus Markdown summary; conversion exit code non-zero on ERROR diagnostics.
</flow>
<contracts>
- Each component exposes pure data contracts (see components/*/SPEC.md) with typed inputs/outputs and explicit error handling; no component may mutate shared global state.
- Paths normalized to posix style internally; filesystem access centralized in discovery/emitter; evaluators operate on supplied content buffers for testability.
- Diagnostics propagated through shared collector interface; no silent drops of unsupported constructs; UnknownConstruct entries emitted alongside diagnostics (code UNKNOWN_CONSTRUCT) with severity-driven behavior (info/warn continue, error may block).
- Config overrides always win over discovered flags/metadata; unknown config keys cause WARN unless `strict=True`.
- Project-global config must remain centralized in root CMake (or dedicated module) and not duplicated across subdirs.
- Namespaced aliases (`Project::Name`) must be generated for internal libraries; linking must prefer alias over raw library names for internal deps.
- Packaging mode must produce install/export and Config.cmake artifacts with consistent namespace/project identifiers.
</contracts>
<testing>
- Requires unit tests per function/class listed in specs; integration suites per scenario.
- Core scenarios (to be materialized as fixtures): TS01 single Makefile single target; TS02 recursive includes; TS03 pattern rules; TS04 conditional branches; TS05 custom command; TS06 missing include; TS07 unknown function; TS08 mixed C/C++; TS09 flag mapping overrides; TS10 ignored paths; TS11 duplicate targets; TS12 unusual file paths (spaces); TS13 dry-run only; TS14 JSON report only; TS15 large project with caching; TS16 unmapped flags warning; TS17 custom rule handling from config; TS18 parallel includes; TS19 object libraries; TS20 static+shared split; TS21 project-global config detection and centralized CMake emission; TS22 namespaced alias linking internal vs external; TS23 INTERFACE/IMPORTED targets; TS24 packaging mode outputs (install/export/config); TS25 global flags vs per-target flags separation; TS26 unknown construct capture/reporting (eval/call/shell/conditional/emitter).
</testing>
<observability>
- Logging hooks at DEBUG/INFO; diagnostics for user-visible issues; timings optional via CLI flag (future) but instrumented at controller layer.
</observability>
<deploy>
- Distributed via pip; entrypoint `gmake2cmake` console_script; should support PyInstaller (avoid dynamic imports at runtime).
</deploy>
</architecture_doc>
