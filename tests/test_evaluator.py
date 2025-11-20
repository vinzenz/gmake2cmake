from __future__ import annotations

from gmake2cmake.config import ConfigModel
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir.unknowns import UnknownConstructFactory
from gmake2cmake.make import evaluator, parser


def test_variable_expansion_and_compile_inference_with_autovars():
    ast = [
        parser.VariableAssign(name="CC", value="gcc", kind="simple", location=parser.SourceLocation("Makefile", 1, 1)),
        parser.Rule(
            targets=["build/foo.o"],
            prerequisites=["src/foo.c", "foo.h"],
            commands=["$(CC) -Iinc -DDEBUG -c $< -o $@"],
            location=parser.SourceLocation("Makefile", 2, 1),
        ),
    ]
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), ConfigModel(), DiagnosticCollector())
    assert facts.inferred_compiles
    compile = facts.inferred_compiles[0]
    assert compile.source == "src/foo.c"
    assert compile.output == "build/foo.o"
    assert compile.includes == ["inc"]
    assert compile.defines == ["DEBUG"]
    assert "-c" not in compile.flags


def test_project_globals_and_feature_toggles():
    ast = [
        parser.VariableAssign(name="WITH_SSL", value="1", kind="simple", location=parser.SourceLocation("config.mk", 1, 1)),
        parser.VariableAssign(name="CFLAGS", value="-O2 -DGLOBAL", kind="simple", location=parser.SourceLocation("config.mk", 2, 1)),
    ]
    cfg = ConfigModel(global_config_files=["config.mk"])
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), cfg, DiagnosticCollector())
    assert facts.project_globals.vars["CFLAGS"] == "-O2 -DGLOBAL"
    assert facts.project_globals.feature_toggles["WITH_SSL"] is True
    assert "GLOBAL" in facts.project_globals.defines
    assert "-O2" in facts.project_globals.flags["c"]
    assert "config.mk" in facts.project_globals.sources


def test_conditionals_and_custom_commands():
    true_rule = parser.Rule(
        targets=["obj/one.o"],
        prerequisites=["one.c"],
        commands=["cc -c $< -o $@"],
        location=parser.SourceLocation("Makefile", 3, 1),
    )
    false_rule = parser.Rule(
        targets=["obj/two.o"],
        prerequisites=["two.c"],
        commands=["echo skip"],
        location=parser.SourceLocation("Makefile", 4, 1),
    )
    ast = [
        parser.VariableAssign(name="MODE", value="debug", kind="simple", location=parser.SourceLocation("Makefile", 1, 1)),
        parser.Conditional(
            test="ifeq ($(MODE),release)", true_body=[true_rule], false_body=[false_rule], location=parser.SourceLocation("Makefile", 2, 1)
        ),
    ]
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), ConfigModel(), DiagnosticCollector())
    assert all(rule.targets != ["obj/one.o"] for rule in facts.rules)
    assert any(cmd.commands[0].expanded == "echo skip" for cmd in facts.custom_commands)


def test_ignore_paths_and_separation():
    ast = [
        parser.Rule(
            targets=["build/skip.o"],
            prerequisites=["skip.c"],
            commands=["cc -c skip.c -o build/skip.o"],
            location=parser.SourceLocation("Makefile", 1, 1),
        ),
        parser.Rule(
            targets=["phony"],
            prerequisites=[],
            commands=["echo hi"],
            location=parser.SourceLocation("Makefile", 2, 1),
        ),
    ]
    cfg = ConfigModel(ignore_paths=["build/*"])
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), cfg, DiagnosticCollector())
    assert not facts.inferred_compiles  # ignored rule
    assert facts.custom_commands and facts.custom_commands[0].commands[0].expanded == "echo hi"


def test_unsupported_function_diagnostic():
    ast = [
        parser.VariableAssign(
            name="LIST", value="$(call DEFINE_RULE,$(target))", kind="simple", location=parser.SourceLocation("Makefile", 1, 1)
        ),
    ]
    diagnostics = DiagnosticCollector()
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), ConfigModel(), diagnostics, unknown_factory=UnknownConstructFactory())
    assert any(d.code == "UNKNOWN_CONSTRUCT" for d in diagnostics.diagnostics)
    assert facts.unknown_constructs and facts.unknown_constructs[0].category == "make_function"


def test_unsupported_function_diagnostic_includes_location():
    """Test that diagnostic messages always include clear location information."""
    ast = [
        parser.VariableAssign(
            name="LIST", value="$(call DEFINE_RULE,$(target))", kind="simple", location=parser.SourceLocation("Makefile", 42, 10)
        ),
    ]
    diagnostics = DiagnosticCollector()
    # Evaluate with default factory (which is created automatically)
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), ConfigModel(), diagnostics)
    # Diagnostic should be emitted with location info
    diag = next((d for d in diagnostics.diagnostics if d.code == "UNKNOWN_CONSTRUCT"), None)
    assert diag is not None
    # Message should contain location information and unknown construct ID
    assert "Makefile" in diag.message
    assert "42" in diag.message
    assert diag.message.startswith("UC")  # Should start with unknown construct ID
    # Unknown constructs should be recorded
    assert len(facts.unknown_constructs) > 0
    uc = facts.unknown_constructs[0]
    assert uc.file == "Makefile"
    assert uc.line == 42
