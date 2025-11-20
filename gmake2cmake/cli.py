from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from gmake2cmake import config as config_module
from gmake2cmake.cmake import emitter as cmake_emitter
from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code, to_console
from gmake2cmake.fs import FileSystemAdapter, LocalFS
from gmake2cmake.ir import builder as ir_builder
from gmake2cmake.ir.unknowns import UnknownConstruct, UnknownConstructFactory
from gmake2cmake.ir.unknowns import to_dict as unknown_to_dict
from gmake2cmake.make import discovery, evaluator
from gmake2cmake.make import parser as make_parser


@dataclass
class CLIArgs:
    source_dir: Path
    entry_makefile: Optional[str]
    output_dir: Path
    config_path: Optional[Path]
    dry_run: bool
    report: bool
    verbose: int
    strict: bool
    processes: Optional[int]
    with_packaging: bool


@dataclass
class RunContext:
    args: CLIArgs
    config: config_module.ConfigModel
    diagnostics: DiagnosticCollector
    filesystem: FileSystemAdapter
    now: Callable[[], datetime]
    unknown_constructs: list[UnknownConstruct] = field(default_factory=list)
    unknown_factory: UnknownConstructFactory = field(default_factory=UnknownConstructFactory)


def parse_args(argv: list[str]) -> CLIArgs:
    parser = argparse.ArgumentParser(prog="gmake2cmake", add_help=True)
    parser.add_argument("--source-dir", default=".", help="Source directory containing Makefiles")
    parser.add_argument("-f", "--entry-makefile", dest="entry_makefile", help="Entry Makefile name")
    parser.add_argument("--output-dir", default="./cmake-out", help="Output directory for CMake files")
    parser.add_argument("--config", dest="config_path", help="YAML config path")
    parser.add_argument("--dry-run", action="store_true", help="Compute outputs without writing files")
    parser.add_argument("--report", action="store_true", help="Write JSON diagnostics report")
    parser.add_argument("--with-packaging", action="store_true", help="Generate install/export/package files")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    parser.add_argument("--strict", action="store_true", help="Treat unknown config keys as errors")
    parser.add_argument("--processes", type=int, help="Number of processes to use")
    parsed = parser.parse_args(argv)
    if not str(parsed.source_dir):
        raise ValueError("source_dir cannot be empty")
    if not str(parsed.output_dir):
        raise ValueError("output_dir cannot be empty")
    return CLIArgs(
        source_dir=Path(parsed.source_dir).expanduser().resolve(),
        entry_makefile=parsed.entry_makefile,
        output_dir=Path(parsed.output_dir).expanduser().resolve(),
        config_path=Path(parsed.config_path).expanduser().resolve() if parsed.config_path else None,
        dry_run=bool(parsed.dry_run),
        report=bool(parsed.report),
        verbose=int(parsed.verbose),
        strict=bool(parsed.strict),
        processes=parsed.processes,
        with_packaging=bool(parsed.with_packaging),
    )


def handle_exception(exc: Exception, diagnostics: DiagnosticCollector) -> None:
    if isinstance(exc, KeyboardInterrupt):  # pragma: no cover - passthrough
        raise
    add(diagnostics, "ERROR", "CLI_UNHANDLED", f"Unhandled exception: {exc}")


def run(
    argv: list[str],
    *,
    fs: Optional[FileSystemAdapter] = None,
    now: Optional[Callable[[], datetime]] = None,
    pipeline_fn: Optional[Callable[[RunContext], None]] = None,
) -> int:
    fs = fs or LocalFS()
    now = now or datetime.utcnow
    try:
        args = parse_args(argv)
    except ValueError as exc:
        diagnostics = DiagnosticCollector()
        handle_exception(exc, diagnostics)
        to_console(diagnostics, stream=_stdout(), verbose=True)
        return exit_code(diagnostics)
    diagnostics = DiagnosticCollector()
    config = config_module.load_and_merge(args, diagnostics, fs)
    ctx = RunContext(args=args, config=config, diagnostics=diagnostics, filesystem=fs, now=now)
    if pipeline_fn:
        try:
            pipeline_fn(ctx)
        except Exception as exc:  # pragma: no cover - pipeline error path
            handle_exception(exc, diagnostics)
    else:
        _default_pipeline(ctx)
    if args.report:
        _write_report(args.output_dir, diagnostics, fs, ctx.unknown_constructs)
    to_console(diagnostics, stream=_stdout(), verbose=bool(args.verbose), unknown_count=len(ctx.unknown_constructs))
    return exit_code(diagnostics)


def _default_pipeline(ctx: RunContext) -> None:
    graph, contents = discovery.discover(ctx.args.source_dir, ctx.args.entry_makefile, ctx.filesystem, ctx.diagnostics)
    if exit_code(ctx.diagnostics) != 0:
        return
    for content in contents:
        parse_result = make_parser.parse_makefile(content.content, content.path, unknown_factory=ctx.unknown_factory)
        for diag in parse_result.diagnostics:
            add(ctx.diagnostics, diag["severity"], diag["code"], diag["message"], diag.get("location"))
        if parse_result.unknown_constructs:
            ctx.unknown_constructs.extend(parse_result.unknown_constructs)
        facts = evaluator.evaluate_ast(
            parse_result.ast,
            evaluator.VariableEnv(),
            ctx.config,
            ctx.diagnostics,
            unknown_factory=ctx.unknown_factory,
        )
        ir_result = ir_builder.build_project(facts, ctx.config, ctx.diagnostics)
        if exit_code(ctx.diagnostics) != 0 or ir_result.project is None:
            continue
        if ir_result.project.unknown_constructs:
            ctx.unknown_constructs.extend(ir_result.project.unknown_constructs)
        options = cmake_emitter.EmitOptions(
            dry_run=ctx.args.dry_run,
            packaging=ctx.config.packaging_enabled,
            namespace=ctx.config.namespace or (ctx.config.project_name or "Project"),
        )
        cmake_emitter.emit(ir_result.project, ctx.args.output_dir, options=options, fs=ctx.filesystem, diagnostics=ctx.diagnostics)


def _write_report(output_dir: Path, diagnostics: DiagnosticCollector, fs: FileSystemAdapter, unknowns: list[UnknownConstruct]) -> None:
    report_path = output_dir / "report.json"
    markdown_path = output_dir / "report.md"
    diag_payload = [
        {
            "severity": d.severity,
            "code": d.code,
            "message": d.message,
            "location": d.location,
            "origin": d.origin,
        }
        for d in diagnostics.diagnostics
    ]
    unknown_payload = [unknown_to_dict(u) for u in unknowns]
    json_report = {"diagnostics": diag_payload, "unknown_constructs": unknown_payload}
    markdown = _render_unknowns_markdown(unknowns)
    try:
        fs.makedirs(report_path.parent)
        fs.write_text(report_path, json.dumps(json_report, sort_keys=True))
        fs.write_text(markdown_path, markdown)
    except Exception as exc:  # pragma: no cover - IO error path
        add(diagnostics, "ERROR", "REPORT_WRITE_FAIL", f"Failed to write report: {exc}")


def _render_unknowns_markdown(unknowns: list[UnknownConstruct]) -> str:
    lines = ["### Unknown Constructs"]
    if not unknowns:
        lines.append("None")
    for uc in unknowns:
        location = uc.file
        if uc.line is not None:
            location += f":{uc.line}"
            if uc.column is not None:
                location += f":{uc.column}"
        targets = ",".join(uc.context.get("targets", []))
        lines.append(
            f"- {uc.id} [{uc.category}] {location} | raw: {uc.raw_snippet} | normalized: {uc.normalized_form} | affects: {targets or 'n/a'} | cmake: {uc.cmake_status} | action: {uc.suggested_action}"
        )
    return "\n".join(lines) + "\n"


def _stdout():
    import sys

    return sys.stdout


def main() -> None:
    code = run(sys.argv[1:])
    raise SystemExit(code)
