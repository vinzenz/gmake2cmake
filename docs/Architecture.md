# Architecture

## Big Picture
```
             +------------------+
  argv ----> |  CLIController   | -- prints summary / JSON
             +---------+--------+
                       |
                       v
         +-------------+--------------+
         |  ConfigManager (YAML, CLI) |
         +-------------+--------------+
                       |
                       v
     +-----------------+------------------+
     |   MakefileDiscoverer (graph)      |
     +-----------------+------------------+
                       |
                       v
       +---------------+----------------+
       |   MakefileParser (AST)         |
       +---------------+----------------+
                       |
                       v
      +----------------+-----------------+
      |   MakeEvaluator (facts + globals)|
      +----------------+-----------------+
                       |
                       v
           +-----------+-----------+
           |      IRBuilder        |
           |  (IR + aliases/global)|
           +-----------+-----------+
                       |
                       v
           +-----------+-----------+
           |     CMakeEmitter      |
           | (CMakeLists, modules) |
           +-----------+-----------+
                       |
                       v
              DiagnosticsReporter
```

## Narrative Walkthrough
- **CLIController** owns the run loop. It parses arguments, loads config, wires components, and decides exit status. Dry-run skips writes; `--with-packaging` tells the emitter to add install/export artifacts.
- **ConfigManager** merges YAML (mapping overrides, ignore lists, link overrides, namespace) with CLI flags. It supplies defaults for global config files (`config.mk`, `rules.mk`, `defs.mk`) and namespace (derived from project name).
- **MakefileDiscoverer** starts from the entry Makefile (explicit `-f` or default) and walks includes/subdir invocations, building a deterministic DAG. Missing mandatory includes and cycles surface as diagnostics.
- **MakefileParser** turns text into AST nodes with source locations (assignments, rules, pattern rules, includes, conditionals). No evaluation occurs here.
- **MakeEvaluator** applies variable expansion, evaluates conditionals, infers compile commands, and classifies “project-global” configuration (files like `config.mk` or assignments before the first rule). It produces BuildFacts: rules, inferred compiles, custom commands, and ProjectGlobals.
- **IRBuilder** converts BuildFacts into the IR `Project`: targets (with physical names and namespaced aliases), sources, dependencies, and `ProjectGlobalConfig`. It classifies libraries as internal/external/imported using build facts and config overrides; internal libs get ALIAS targets (`Namespace::name`).
- **CMakeEmitter** renders root and subdir `CMakeLists.txt`, plus `ProjectGlobalConfig.cmake` when globals exist. It emits ALIAS targets for internals, keeps externals raw, supports INTERFACE/IMPORTED targets, and optionally generates packaging artifacts (`install()`, exports, `MyProjectConfig.cmake`, version file) honoring the namespace.
- **DiagnosticsReporter** aggregates INFO/WARN/ERROR across the pipeline, renders console/JSON, and drives exit codes (ERROR → non-zero).

## Data Highlights
- **Project**: name, version, namespace, languages, targets, `ProjectGlobalConfig`, diagnostics.
- **ProjectGlobalConfig**: global vars/flags/defines/includes/feature toggles + source file provenance. Centralized in root CMake or a module that subdirs include.
- **Target**: physical CMake target name and optional alias (`Namespace::Name`), type (exe/shared/static/object/custom/interface/imported), sources, includes, defines, options, link options, link libs, deps, usage visibility.

## Linkage Rules (human-readable)
- Internal libs: built inside the project → create physical target (e.g., `myproject_libfoo`) and ALIAS `Namespace::foo`; link internal deps via the alias.
- External libs: no build rule / outside tree → stay as raw link items (`m`, `pthread`, `/opt/libbar.a`) unless config overrides map them to imported targets.
- Imported targets: config can force a prebuilt lib into an IMPORTED target with a chosen alias; emitter links that target directly.
- Usage requirements: flags/includes needed by consumers become PUBLIC/INTERFACE; warning/optimization flags stay PRIVATE.

## Global Config Handling
```
Makefiles
  |- config.mk (vars, flags)  \
  |- rules.mk                 |--> ProjectGlobals (vars/flags/defines/includes, feature toggles, sources)
  |- defs.mk                  /
  |- root assignments before first rule
```
IRBuilder merges these into `ProjectGlobalConfig`; CMakeEmitter centralizes them in the root and/or `ProjectGlobalConfig.cmake` to avoid duplication in subdirs.

## Packaging Mode
- Enabled by `--with-packaging` or config flag.
- Emits `install(TARGETS ... EXPORT ...)`, header installs, exports with namespace, and `MyProjectConfig.cmake` + version file so downstreams can `find_package(MyProject REQUIRED)` and link `MyProject::foo`.

Links: [Top-level Architecture spec](../Architecture.md)
