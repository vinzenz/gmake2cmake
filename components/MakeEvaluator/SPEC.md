<component_spec name="MakeEvaluator">
<package>gmake2cmake.make.evaluator</package>
<purpose>Evaluate Makefile AST with variable/function expansion, resolve rules, infer compilation commands, and produce build facts for IRBuilder.</purpose>
<dependencies>
- ConfigModel for overrides and ignore lists.
- DiagnosticsReporter for unsupported constructs.</dependencies>
<data>
- class VariableEnv: mapping(str -> str) with methods set_simple, set_recursive, append; supports automatic variables ($@, $<, $^, $?, $*).
- class EvaluatedCommand: raw(str), expanded(str), location(SourceLocation).
- class EvaluatedRule: targets(list[str]), prerequisites(list[str]), commands(list[EvaluatedCommand]), is_pattern(bool), location(SourceLocation).
- class InferredCompile: source(str), output(str), language(str), flags(list[str]), includes(list[str]), defines(list[str]), location(SourceLocation).
- class ProjectGlobals: vars(dict[str,str]), flags(dict[str,list[str]] keyed by language/all), defines(list[str]), includes(list[str]), feature_toggles(dict[str,str|bool]), sources(list[str] capturing config files).
- class BuildFacts: rules(list[EvaluatedRule]), inferred_compiles(list[InferredCompile]), custom_commands(list[EvaluatedRule]), project_globals(ProjectGlobals), diagnostics(list[Diagnostic]).
- UnknownConstruct entries may be emitted for unsupported functions/conditionals/shell commands with category make_function/conditional_logic/shell_command and propagated downstream.
</data>
<functions>
  <function name="evaluate_ast" signature="evaluate_ast(nodes: list[ASTNode], env: VariableEnv, config: ConfigModel, diagnostics: DiagnosticCollector) -> BuildFacts">
  - Iterates AST nodes applying assignments/conditionals to env; expands variables using recursive or simple semantics; honors config.ignore_paths to skip nodes.
  - Detects project-global config context: files named config.mk/rules.mk/defs.mk (configurable via ConfigModel.global_config_files) and assignments appearing before the first rule in a translation unit are classified into ProjectGlobals (vars/flags/defines/includes/feature_toggles) with source file recorded.
  - Executes conditional tests using simple textual comparison; unsupported functions emit WARN EVAL_UNSUPPORTED_FUNC and create UnknownConstruct (category make_function/conditional_logic) with normalized_form (e.g., eval(call(...))) and impact metadata.</function>
  <function name="expand_variables" signature="expand_variables(value: str, env: VariableEnv, location: SourceLocation, diagnostics: DiagnosticCollector) -> str">
  - Supports $(VAR) and ${VAR}; supports built-in automatic variables when provided by caller; detects recursive loops -> ERROR EVAL_RECURSIVE_LOOP.</function>
  <function name="expand_rule" signature="expand_rule(rule: Rule|PatternRule, env: VariableEnv, diagnostics: DiagnosticCollector) -> EvaluatedRule">
  - Applies variable expansion to targets/prereqs/commands; attaches autovars ($@, $<, $^) per command; pattern rules mark is_pattern=True.</function>
  <function name="infer_compiles" signature="infer_compiles(rules: list[EvaluatedRule], config: ConfigModel, diagnostics: DiagnosticCollector) -> list[InferredCompile]">
  - Detects compile commands by matching known compiler prefixes (cc, gcc, clang, c++, g++, clang++); extracts -I/-D/-o flags; determines language from compiler or source extension.
  - Unknown flags collected as pass-through; if no source inferred -> WARN EVAL_NO_SOURCE.</function>
  <function name="separate_custom_commands" signature="separate_custom_commands(rules: list[EvaluatedRule]) -> tuple[list[EvaluatedRule], list[EvaluatedRule]]">
  - Splits build vs custom shell rules (heuristic: commands without compiler/linker patterns treated as custom); preserves order.</function>
  - UnknownConstructs from shell commands that cannot be mapped should carry category shell_command and suggested_action manual_custom_command.</function>
</functions>
<contracts>
- Variable expansion deterministic; whitespace preserved except where normalization defined.
- Pattern rule expansion must not emit concrete outputs; IRBuilder handles instantiation based on prerequisites when possible.
- BuildFacts must always returned even on errors to allow partial IR build.
- No filesystem access; all content provided as strings.</contracts>
<testing>
- Recursive vs simple variable behavior; append handling.
- Conditional evaluation with ifeq/ifneq/ifdef/ifndef (including unknown branches captured as UnknownConstruct).
- Autovar substitution correctness in commands.
- Compile command inference for C/C++/ASM; detection of missing -o target.
- Unsupported function triggers WARN but continues.
- Global config detection from config.mk/defs.mk/rules.mk and pre-rule assignments populating ProjectGlobals.</testing>
</component_spec>
