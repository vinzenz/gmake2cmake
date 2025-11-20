# ConfigManager

Keeps configuration predictable and explicit.

```
YAML + CLI flags --load--> raw dict --parse--> ConfigModel
                                   \
                                    \-- diagnostics (WARN/ERROR on schema issues)
                                   \
                                    \-- defaults (namespace, global_config_files)
```

- **Purpose**: Load and validate YAML settings, merge CLI defaults, and provide normalized config knobs (mappings, ignore lists, global config hints, namespaces, packaging flag).
- **Inputs**: CLIArgs (source/output paths, strict, with_packaging), YAML file via fs adapter.
- **Outputs**: `ConfigModel` with normalized paths, default `global_config_files` (config.mk/rules.mk/defs.mk), namespace (sanitized project name when missing), packaging_enabled flag, link overrides, target/flag mappings.
- **Behavior details**:
  - Uses `safe_load`; rejects non-mapping root with CONFIG_SCHEMA errors.
  - Unknown keys → WARN or ERROR (strict mode).
  - Normalizes ignore paths to posix; deduplicates lists deterministically.
  - Classifies library overrides (internal/external/imported) and keeps alias/imported target hints.
- **Interactions**:
  - CLIController: `load_and_merge`.
  - MakeEvaluator: consumes ignore paths and `global_config_files`.
  - IRBuilder: uses flag/target/link overrides, namespace, packaging flag.
  - CMakeEmitter: gets namespace + packaging flag for emission choices.
- **Spec**: [components/ConfigManager/SPEC.md](../../components/ConfigManager/SPEC.md)
