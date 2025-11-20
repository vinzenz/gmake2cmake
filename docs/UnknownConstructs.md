# Unknown Constructs

Structured representation of unsupported/unmapped Makefile patterns captured during migration.

- **Model**: `UnknownConstruct` with fields
  - `id`: stable UCxxxx
  - `category`: `make_syntax` | `make_function` | `shell_command` | `conditional_logic` | `toolchain_specific` | `other`
  - `file`, `line`, `column`
  - `raw_snippet` (trimmed), `normalized_form` (best-effort structural)
  - `context`: `targets`, `variables_in_scope`, `includes_stack`
  - `impact`: `phase` (`parse` | `evaluate` | `build_graph` | `cmake_generation`), `severity` (`info` | `warning` | `error`)
  - `cmake_status`: `not_generated` | `partially_generated` | `approximate`
  - `suggested_action`: e.g., `manual_review`, `manual_custom_command`, `requires_mapping`
- **Normalization**:
  - Functions: `$(eval $(call DEFINE_RULE,$(t)))` -> `eval(call(DEFINE_RULE, $(t)))`
  - Shell commands: `$(shell perl gen.pl ...)` -> `shell(perl gen.pl ...)`
  - Conditionals: `if CC contains clang: add -Weverything to CFLAGS`
  - Fallback to raw_snippet when parsing fails.
- **Lifecycle**:
  - Created in parser (unknown syntax), evaluator (functions/conditionals), shell/custom-command mapping, emitter (unmappable toolchain constructs).
  - Stored on `Project.unknown_constructs` and surfaced via Diagnostic code `UNKNOWN_CONSTRUCT` (severity from impact).
- **Reporting**:
  - JSON report includes `unknown_constructs` DTOs.
  - Markdown report adds `### Unknown Constructs` section with one-line entries (id/category/location/snippet/normalized/targets/status/action).
  - Console shows count only: `N unknown constructs (see report for details).`
