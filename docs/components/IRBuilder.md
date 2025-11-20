# IRBuilder

Builds a normalized, CMake-friendly IR from raw BuildFacts.

```
BuildFacts + ConfigModel
   -> project metadata (name/version/namespace/languages)
   -> ProjectGlobalConfig (globals merged)
   -> targets (physical + alias) + sources + deps
```

- **Purpose**: Convert BuildFacts into an IR `Project` ready for emission, including alias naming and library classification.
- **Inputs**: `BuildFacts` (with `ProjectGlobals`), `ConfigModel` (mappings, ignores, link overrides, namespace), diagnostics.
- **Outputs**: `IRBuildResult` with populated Project and diagnostics.
- **Behavior details**:
  - Computes project name/version/namespace; collects languages from inferred compiles.
  - Normalizes ProjectGlobals into `ProjectGlobalConfig` (includes/flags/defines/feature toggles, provenance), applying flag mappings and ignore rules.
  - Groups inferred compiles by output artifact → target type selection; creates INTERFACE targets for shared flag bundles when needed; creates IMPORTED targets for configured prebuilt libs.
  - Applies target mappings (rename/type/visibility/link/includes/defines/options) and flag mappings; deduplicates sources.
  - Classifies libraries internal vs external using build facts (presence of build rule, location) and `link_overrides`; assigns physical names (e.g., `myproject_libfoo`) and namespaced aliases (`Namespace::foo`) for internals; externals stay raw; imported targets use configured identifiers.
  - Attaches dependencies from rule prerequisites, preferring alias names for internals; validates uniqueness and references.
- **Interactions**: Produces IR consumed by CMakeEmitter; uses ConfigManager helpers for flag and link overrides; diagnostics flow through shared collector.
- **Spec**: [components/IRBuilder/SPEC.md](../../components/IRBuilder/SPEC.md)
