from __future__ import annotations

from gmake2cmake.config import ConfigModel
from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.make import evaluator, parser


def test_variable_expansion_and_compile_inference():
    ast = [
        parser.VariableAssign(name="CC", value="gcc", kind="simple", location=parser.SourceLocation("Makefile", 1, 1)),
        parser.Rule(
            targets=["foo.o"],
            prerequisites=["foo.c"],
            commands=["gcc -Iinc -DFLAG -c foo.c -o foo.o"],
            location=parser.SourceLocation("Makefile", 2, 1),
        ),
    ]
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), ConfigModel(), DiagnosticCollector())
    assert facts.inferred_compiles
    compile = facts.inferred_compiles[0]
    assert compile.source == "foo.c"
    assert compile.output == "foo.o"
    assert "inc" in compile.includes
    assert "FLAG" in compile.defines[0]


def test_project_globals_detection():
    ast = [
        parser.VariableAssign(name="CFLAGS", value="-O2", kind="simple", location=parser.SourceLocation("config.mk", 1, 1)),
        parser.VariableAssign(name="CPPFLAGS", value="-Iinc", kind="simple", location=parser.SourceLocation("config.mk", 2, 1)),
    ]
    cfg = ConfigModel(global_config_files=["config.mk"])
    facts = evaluator.evaluate_ast(ast, evaluator.VariableEnv(), cfg, DiagnosticCollector())
    assert facts.project_globals.vars["CFLAGS"] == "-O2"
    assert "config.mk" in facts.project_globals.sources
