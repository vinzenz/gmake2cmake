<component_spec name="DiagnosticsReporter">
<package>gmake2cmake.diagnostics</package>
<purpose>Collect, deduplicate, and render diagnostics across pipeline; provide console and JSON output plus exit-code logic.</purpose>
<dependencies>json module only; accepts injected stream for console output to enable test control.</dependencies>
<data>
- class Diagnostic: severity(enum INFO/WARN/ERROR), code(str), message(str), location(str|None), origin(str|None).
- class DiagnosticCollector: diagnostics(list[Diagnostic]).
</data>
<functions>
  <function name="add" signature="add(collector: DiagnosticCollector, severity: str, code: str, message: str, location: str|None=None, origin: str|None=None) -> None">
  - Appends diagnostic; severity validated; deduplicates identical (severity+code+message+location+origin).</function>
  <function name="extend" signature="extend(collector: DiagnosticCollector, items: list[Diagnostic]) -> None">
  - Adds multiple diagnostics preserving order; applies deduplication.</function>
  <function name="has_errors" signature="has_errors(collector: DiagnosticCollector) -> bool">
  - Returns True if any severity==ERROR.</function>
  <function name="to_console" signature="to_console(collector: DiagnosticCollector, *, stream: TextIO, verbose: bool) -> None">
  - Renders summary lines `[{severity}] {code}: {message} ({location})`; verbose=True includes origin and counts; sorted by severity DESC then code.</function>
  <function name="to_json" signature="to_json(collector: DiagnosticCollector) -> str">
  - Returns deterministic JSON string array of dicts; preserves insertion order.</function>
  <function name="exit_code" signature="exit_code(collector: DiagnosticCollector) -> int">
  - Returns 1 if has_errors else 0.</function>
</functions>
<contracts>
- Diagnostics are append-only; deduplication must not drop differing origins.
- JSON output must be stable for tests (sorted keys).
- No direct printing; console rendering uses provided stream (stdout in CLIController).</contracts>
<testing>
- Deduplication of identical diagnostics.
- Console formatting with/without location; verbose adds origin.
- JSON serialization stable ordering.
- exit_code behavior when WARN-only vs ERROR present.</testing>
</component_spec>
