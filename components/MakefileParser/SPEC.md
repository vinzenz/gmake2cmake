<component_spec name="MakefileParser">
<package>gmake2cmake.make.parser</package>
<purpose>Convert Makefile text into an AST covering variables, rules, pattern rules, includes, and conditionals, preserving source locations for diagnostics.</purpose>
<dependencies>
- DiagnosticsReporter for syntax issues.
</dependencies>
<data>
- class SourceLocation: path(str), line(int), column(int).
- AST nodes (immutable dataclasses):
  - VariableAssign: name(str), value(str), kind(enum{'simple','recursive','append'}), location(SourceLocation).
  - Rule: targets(list[str]), prerequisites(list[str]), commands(list[str]), location(SourceLocation).
  - PatternRule: target_pattern(str), prereq_patterns(list[str]), commands(list[str]), location(SourceLocation).
  - IncludeStmt: paths(list[str]), optional(bool), location(SourceLocation).
  - Conditional: test(str raw), true_body(list[ASTNode]), false_body(list[ASTNode]), location(SourceLocation).
  - RawCommand: command(str), location(SourceLocation) for bare shell lines.
- class ParseResult: ast(list[ASTNode]), diagnostics(list[Diagnostic]), unknown_constructs(list[UnknownConstruct]) for unsupported/unknown syntax/directives.
</data>
<functions>
  <function name="parse_makefile" signature="parse_makefile(content: str, path: str) -> ParseResult">
  - Splits lines with newline preservation; handles line continuations with backslash; strips comments except escaped \#.
  - Detects assignments (=, :=, +=); detects rule lines with ':'; pattern rules with '%' in target.
  - Collects include/-include statements but does not resolve paths (handled by discovery).
  - Parses conditionals (`ifeq`, `ifneq`, `ifdef`, `ifndef`, `else`, `endif`) building nested Conditional nodes; unmatched conditional -> ERROR PARSER_CONDITIONAL.
  - On unsupported or malformed syntax, create UnknownConstruct(category=make_syntax) with location/snippet/normalized_form and add to ParseResult.unknown_constructs plus Diagnostic code UNKNOWN_CONSTRUCT (severity derived from impact).</function>
  <function name="parse_commands" signature="parse_commands(lines: list[str], start_index: int, path: str) -> tuple[list[str], int]">
  - Consumes indented command lines for a rule; stops at first non-indented; returns commands and next index.</function>
  <function name="normalize_tokens" signature="normalize_tokens(token: str) -> str">
  - Collapses repeated whitespace to single spaces except inside $( ... ) expansions; used for deterministic comparisons.</function>
</functions>
<contracts>
- Parser must be streaming-friendly; no filesystem access.
- Every AST node carries SourceLocation.
- Invalid syntax produces ERROR diagnostics with location and offending line; parser continues collecting further nodes when safe.
- No evaluation of variables; leaves expansions intact for evaluator.
- Unknown or unsupported constructs must be recorded as UnknownConstructs (not dropped) with best-effort normalization and location.</contracts>
<testing>
- Assignment types recognized; verify recursive vs simple.
- Line continuation merges lines preserving spaces.
- Commands grouping under rules; pattern rule detection.
- Conditional nesting depth >2; unmatched endif error.
- Include parsing with optional flag detection.
- Unknown syntax captured into unknown_constructs with matching diagnostics.</testing>
</component_spec>
