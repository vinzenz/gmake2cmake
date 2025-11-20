# DiagnosticsReporter

Keeps user-facing messaging consistent and machine-readable.

```
diagnostics collected everywhere
  -> deduplicate
  -> console summary (verbosity aware)
  -> JSON report (deterministic ordering)
  -> exit code (ERROR? -> 1 else 0)
```

- **Purpose**: Aggregate diagnostics across the pipeline, present them to humans, and inform process exit.
- **Inputs**: Shared `DiagnosticCollector` populated by all components; output stream for console rendering.
- **Outputs**: Console summary, JSON string (CLI may write to file), `has_errors` boolean, exit code int.
- **Behavior details**:
  - `add/extend` deduplicate on `(severity, code, message, location, origin)`.
  - `to_console` formats `[SEVERITY] CODE: message (location)`; verbose adds origin and counts.
  - `to_json` produces stable JSON array with sorted keys for testability.
  - `exit_code` returns 1 when any ERROR exists.
- **Interactions**: CLIController invokes console/JSON rendering; links into CI/CLI exit behavior; no direct printing beyond provided stream.
- **Spec**: [components/DiagnosticsReporter/SPEC.md](../../components/DiagnosticsReporter/SPEC.md)
