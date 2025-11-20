# MakeEvaluator

Executes the Make “logic” enough to derive build facts and global config.

```
AST --expand vars/conds--> evaluated rules + commands
           \
            \-- infer compiles (-I/-D/-o, compiler/lang)
             \
              \-- capture ProjectGlobals (config.mk, pre-rule assigns)
```

- **Purpose**: Produce BuildFacts: evaluated rules/commands, inferred compile actions, custom commands, and `ProjectGlobals`.
- **Inputs**: AST nodes, `VariableEnv`, `ConfigModel` (ignores, `global_config_files`), diagnostics.
- **Outputs**: `BuildFacts` (rules, inferred_compiles, custom_commands, ProjectGlobals, diagnostics).
- **Behavior details**:
  - Variable expansion supports simple/recursive vars and autovars (`$@`, `$<`, `$^`, `$?`, `$*`); detects recursive loops.
  - Conditional handling for `ifeq`/`ifneq`/`ifdef`/`ifndef`.
  - Compile inference matches compiler prefixes (cc/gcc/clang/c++/g++/clang++), extracts `-I/-D/-o`, derives language from compiler or source extension, warns when no source/target found.
  - Project-global capture: assignments from files named in `global_config_files` (config.mk/rules.mk/defs.mk by default) or from top-level statements before the first rule become `ProjectGlobals` (vars/flags/defines/includes/feature_toggles) with provenance.
- **Interactions**: Feeds `BuildFacts` to IRBuilder; respects ignore paths from ConfigManager; diagnostics passed to DiagnosticsReporter.
- **Spec**: [components/MakeEvaluator/SPEC.md](../../components/MakeEvaluator/SPEC.md)
