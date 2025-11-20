<component_spec name="CLIController">
<package>gmake2cmake.cli</package>
<purpose>Entry CLI, argument parsing, lifecycle orchestration, exit-code management, wiring diagnostics and downstream components.</purpose>
<dependencies>
- ConfigManager for YAML merge/validation.
- MakefileDiscoverer -> MakefileParser -> MakeEvaluator -> IRBuilder -> CMakeEmitter.
- DiagnosticsReporter shared collector.
</dependencies>
<data>
- class CLIArgs: source_dir(Path), entry_makefile(str|None), output_dir(Path), config_path(Path|None), dry_run(bool), report(bool), verbose(int), strict(bool), processes(int|None), with_packaging(bool).
- class RunContext: args(CLIArgs), config(ConfigModel), diagnostics(DiagnosticCollector), filesystem(FileSystemAdapter stub for tests), clock callable for timestamps.
</data>
<functions>
  <function name="parse_args" signature="parse_args(argv: list[str]) -> CLIArgs">
  - Uses argparse; default source_dir='.'; default output_dir='./cmake-out'; default entry_makefile='Makefile' unless -f provided.
  - Adds flag `--with-packaging` (default False) to toggle install/export generation; boolean stored as with_packaging.
  - Validates paths are not empty; expands user/home; converts to absolute Paths.
  - On invalid args, raises ValueError with message and no sys.exit to keep testability.</function>
  <function name="run" signature="run(argv: list[str], *, fs: FileSystemAdapter, now: Callable[[], datetime]|None=None) -> int">
  - Flow: args=parse_args(argv); diagnostics=DiagnosticCollector(); config=ConfigManager.load_and_merge(args, diagnostics, fs).
  - resolve entry via MakefileDiscoverer; parse/evaluate/build IR; emit CMake with packaging and namespace derived from config/project name; render diagnostics/report; return exit code (0 if no ERROR, else 1).
  - Honors dry_run: skip writes, still parse/evaluate/build/emitter returns buffers only.
  - Honors verbose: toggles diagnostics detail; strict: passed to ConfigManager and evaluators for error handling.
  - Passes with_packaging flag to emitter to control install/export generation.</function>
  <function name="wire_pipeline" signature="wire_pipeline(ctx: RunContext) -> PipelineBundle">
  - Prepares component instances with shared diagnostics and config; returns struct containing discoverer, parser, evaluator, ir_builder, emitter, reporter.
  - Ensures each component receives fs adapter and deterministic options.</function>
  <function name="handle_exception" signature="handle_exception(exc: Exception, diagnostics: DiagnosticCollector) -> None">
  - Converts unexpected exceptions into ERROR diagnostic with code=CLI_UNHANDLED; does not swallow KeyboardInterrupt (re-raise).</function>
</functions>
<contracts>
- parse_args must be pure; no filesystem access.
- run must not call sys.exit; returns int; all side effects via fs adapter; log/print delegated to DiagnosticsReporter.
- Paths normalized to absolute, posix-like for downstream.
- Exit code 1 if any DiagnosticsReporter.has_errors() else 0; non-fatal WARN/INFO allowed.
- Commands executed in order; pipeline steps must short-circuit on fatal diagnostics (ERROR) before emitting CMake.</contracts>
<testing>
- Arg parsing: defaults, custom -f, invalid path strings.
- Dry-run: no fs writes invoked (fs adapter spy).
- Error path: missing Makefile triggers ERROR via discoverer, run returns 1.
- Verbosity toggles detail in reporter payload.
- Strict mode: unknown config key causes ERROR propagation from ConfigManager.
</testing>
</component_spec>
