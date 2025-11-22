# CLIController

Human-focused view of what it does and how it connects everything.

```
argv
  -> parse_args (argparse, no sys.exit)
  -> config = ConfigManager.load_and_merge(...)
  -> discoverer -> parser -> evaluator -> ir_builder -> emitter
  -> DiagnosticsReporter.{to_console,to_json}
  -> exit code (errors? 1 : 0)
```

- **Purpose**: Own the full run loop and be the only place dealing with CLI UX (flags, exit codes, dry-run/write, packaging toggle).
- **Inputs**: `argv`, `FileSystemAdapter`, optional `clock`. Consumes merged `ConfigModel` from ConfigManager.
- **Outputs**: Exit code; console diagnostics; optional JSON report file (diagnostics, unknowns, introspection summary); generated CMake files (unless dry-run).
- **Behavior details**:
  - Recognizes: `--source-dir`, `-f/--entry-makefile`, `--output-dir`, `--config`, `--dry-run`, `--report`, `--with-packaging`, `--use-make-introspection`, verbosity, strict, processes.
  - Short-circuits pipeline when fatal diagnostics appear before emission.
  - Passes `EmitOptions` (dry_run, packaging, namespace) to CMakeEmitter; ensures diagnostics collector is shared end-to-end.
  - When `--use-make-introspection` is set, logs introspection timing at verbose levels and records summary counts (validated/modified/mismatches/failures) into report outputs; introspection warnings remain WARN-only and do not change exit codes.
  - Never calls `sys.exit`; returns int.
- **Why it matters**: Keeps side effects contained; everything else stays testable/pure.
- **Spec**: [components/CLIController/SPEC.md](../../components/CLIController/SPEC.md)
