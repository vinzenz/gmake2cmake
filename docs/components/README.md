# Components

High-level map:
```
CLIController
  -> ConfigManager
  -> MakefileDiscoverer -> MakefileParser -> MakeEvaluator
  -> IRBuilder -> CMakeEmitter
  -> DiagnosticsReporter
```

- [CLIController](CLIController.md) — entrypoint run loop and wiring
- [ConfigManager](ConfigManager.md) — config load/merge/validation
- [MakefileDiscoverer](MakefileDiscoverer.md) — include/subdir graph builder
- [MakefileParser](MakefileParser.md) — Makefile to AST
- [MakeEvaluator](MakeEvaluator.md) — AST evaluation, build facts, project globals
- [IRBuilder](IRBuilder.md) — IR construction, alias assignment, linking roles
- [CMakeEmitter](CMakeEmitter.md) — CMakeLists generation, globals, packaging
- [DiagnosticsReporter](DiagnosticsReporter.md) — diagnostic aggregation/output
