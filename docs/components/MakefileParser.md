# MakefileParser

Turns raw Makefile text into a structured AST.

```
Makefile text --tokenize--> AST nodes (assignments/rules/includes/conditionals)
                         \
                          \-- diagnostics (syntax issues)
```

- **Purpose**: Provide a loss-aware AST with source locations before any evaluation.
- **Inputs**: `MakefileContent` (path + text).
- **Outputs**: `ParseResult` with AST nodes and diagnostics.
- **Behavior details**:
  - Handles line continuations, strips comments (honors escaped `#`), recognizes `=`, `:=`, `+=`.
  - Detects rules (`targets: prereqs`), pattern rules (`%`), indented command blocks, include/-include statements.
  - Parses conditionals (`ifeq`/`ifneq`/`ifdef`/`ifndef`/`else`/`endif`); mismatched nesting → ERROR with location.
- **Interactions**: Feeds AST to MakeEvaluator; diagnostics flow upward through CLIController/DiagnosticsReporter. No filesystem or variable evaluation here.
- **Spec**: [components/MakefileParser/SPEC.md](../../components/MakefileParser/SPEC.md)
