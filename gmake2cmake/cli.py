from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TextIO

from gmake2cmake import config as config_module
from gmake2cmake.cmake import emitter as cmake_emitter
from gmake2cmake.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROJECT_NAME,
    DEFAULT_SOURCE_DIR,
    REPORT_JSON_FILENAME,
    REPORT_MD_FILENAME,
)
from gmake2cmake.diagnostics import DiagnosticCollector, add, exit_code, to_console
from gmake2cmake.fs import FileSystemAdapter, LocalFS
from gmake2cmake.ir import builder as ir_builder
from gmake2cmake.ir.unknowns import UnknownConstruct, UnknownConstructFactory
from gmake2cmake.ir.unknowns import to_dict as unknown_to_dict
from gmake2cmake.logging_config import log_stage, setup_logging
from gmake2cmake.make import discovery, evaluator
from gmake2cmake.make import parser as make_parser
from gmake2cmake.markdown_reporter import MarkdownReporter
from gmake2cmake.profiling import disable_profiling, enable_profiling, get_metrics


@dataclass
class CLIArgs:
    """Parsed command-line arguments for gmake2cmake.

    Attributes:
        source_dir: Root directory containing Makefiles to convert
        entry_makefile: Optional specific Makefile to start conversion from
        output_dir: Directory where CMakeLists.txt will be written
        config_path: Optional path to YAML configuration file
        dry_run: If True, compute outputs without writing files
        report: If True, write JSON diagnostics and markdown report
        verbose: Verbosity level (0=quiet, 1=warnings, 2=info, 3+=debug)
        strict: If True, treat unknown config keys as errors
        processes: Optional number of processes for parallel operations
        with_packaging: If True, generate install/export/package files
        log_file: Optional path to write structured logs
        validate_config: If True, validate config and exit without conversion
    """

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
    log_file: Optional[Path] = None
    profile: bool = False
    validate_config: bool = False


@dataclass
class RunContext:
    """Execution context passed through the pipeline.

    Attributes:
        args: Parsed command-line arguments
        config: Configuration model loaded from YAML
        diagnostics: Collector for diagnostic messages and errors
        filesystem: File system adapter (for testing/modularity)
        now: Callable that returns current datetime
        unknown_constructs: List of constructs that could not be handled
        unknown_factory: Factory for creating UnknownConstruct instances
    """

    args: CLIArgs
    config: config_module.ConfigModel
    diagnostics: DiagnosticCollector
    filesystem: FileSystemAdapter
    now: Callable[[], datetime]
    unknown_constructs: list[UnknownConstruct] = field(default_factory=list)
    unknown_factory: UnknownConstructFactory = field(default_factory=UnknownConstructFactory)


def parse_args(argv: list[str]) -> CLIArgs:
    """Parse and return command-line arguments.

    Provides comprehensive help text and examples for gmake2cmake usage.

    Args:
        argv: Command-line arguments to parse (typically sys.argv[1:])

    Returns:
        CLIArgs instance with parsed arguments

    Raises:
        ValueError: If required arguments are invalid
    """
    parser = argparse.ArgumentParser(
        prog="gmake2cmake",
        add_help=True,
        description="Convert GNU Make projects to CMake",
        epilog="""
Examples:
  gmake2cmake --source-dir . --output-dir cmake-out
  gmake2cmake -f src/Makefile -vv --config config.yaml
  gmake2cmake --dry-run --report --with-packaging
  gmake2cmake --profile --log-file debug.log
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        help="Root directory containing Makefiles (default: %(default)s)",
    )
    parser.add_argument(
        "-f",
        "--entry-makefile",
        dest="entry_makefile",
        help="Specific Makefile to start from (e.g., Makefile, makefile.gnu)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write generated CMakeLists.txt files (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to YAML configuration file for conversion settings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview outputs without writing files",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write JSON diagnostics and markdown report (report.json, report.md)",
    )
    parser.add_argument(
        "--with-packaging",
        action="store_true",
        help="Generate install/export/package CMake rules",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v (warn), -vv (info), -vvv (debug)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat unknown config keys as errors",
    )
    parser.add_argument(
        "--processes",
        type=int,
        help="Number of parallel processes to use (default: auto-detect)",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        help="Write structured logs to file (in addition to console)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Collect and report performance metrics for pipeline stages",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit without conversion",
    )
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
        log_file=Path(parsed.log_file).expanduser().resolve() if parsed.log_file else None,
        profile=bool(parsed.profile),
        validate_config=bool(parsed.validate_config),
    )


def handle_exception(exc: Exception, diagnostics: DiagnosticCollector) -> None:
    """Handle unhandled exceptions by recording them as diagnostics.

    Args:
        exc: The exception that was raised
        diagnostics: Collector to add error diagnostic to

    Raises:
        KeyboardInterrupt: Re-raised without recording as diagnostic

    Returns:
        None
    """
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

    # Set up logging early, before loading config
    setup_logging(verbosity=args.verbose, log_file=args.log_file)

    # Set up profiling if requested
    if args.profile:
        enable_profiling()

    diagnostics = DiagnosticCollector()
    config = config_module.load_and_merge(args, diagnostics, fs)
    ctx = RunContext(args=args, config=config, diagnostics=diagnostics, filesystem=fs, now=now)

    # Handle config validation mode
    if args.validate_config:
        to_console(diagnostics, stream=_stdout(), verbose=bool(args.verbose))
        if exit_code(diagnostics) == 0:
            _stdout().write("Configuration is valid.\n")
        return exit_code(diagnostics)

    try:
        if pipeline_fn:
            try:
                pipeline_fn(ctx)
            except KeyboardInterrupt:  # pragma: no cover - passthrough
                raise
            except Exception as exc:  # pragma: no cover - unexpected pipeline error path
                handle_exception(exc, diagnostics)
        else:
            _default_pipeline(ctx)
    finally:
        # Print profiling summary if enabled
        if args.profile:
            disable_profiling()
            metrics = get_metrics()
            if metrics.stage_timings:
                to_console(DiagnosticCollector(), stream=_stdout(), verbose=False)  # Empty line
                logger = logging.getLogger("gmake2cmake.profile")
                logger.info(metrics.get_summary())

    if args.report:
        project_name = ctx.config.project_name or ctx.args.source_dir.name or DEFAULT_PROJECT_NAME
        _write_report(args.output_dir, diagnostics, fs, ctx.unknown_constructs, project_name=project_name)
    to_console(diagnostics, stream=_stdout(), verbose=bool(args.verbose), unknown_count=len(ctx.unknown_constructs))
    return exit_code(diagnostics)


def _default_pipeline(ctx: RunContext) -> None:
    log_stage("discover", verbosity=ctx.args.verbose)
    graph, contents = discovery.discover(ctx.args.source_dir, ctx.args.entry_makefile, ctx.filesystem, ctx.diagnostics)
    if exit_code(ctx.diagnostics) != 0:
        return
    for content in contents:
        log_stage(f"parse:{content.path}", verbosity=ctx.args.verbose)
        parse_result = make_parser.parse_makefile(content.content, content.path, unknown_factory=ctx.unknown_factory)
        for diag in parse_result.diagnostics:
            add(ctx.diagnostics, diag["severity"], diag["code"], diag["message"], diag.get("location"))
        if parse_result.unknown_constructs:
            ctx.unknown_constructs.extend(parse_result.unknown_constructs)
        log_stage(f"evaluate:{content.path}", verbosity=ctx.args.verbose)
        facts = evaluator.evaluate_ast(
            parse_result.ast,
            evaluator.VariableEnv(),
            ctx.config,
            ctx.diagnostics,
            unknown_factory=ctx.unknown_factory,
        )
        log_stage(f"build:{content.path}", verbosity=ctx.args.verbose)
        ir_result = ir_builder.build_project(facts, ctx.config, ctx.diagnostics)
        if exit_code(ctx.diagnostics) != 0 or ir_result.project is None:
            continue
        if ir_result.project.unknown_constructs:
            ctx.unknown_constructs.extend(ir_result.project.unknown_constructs)
        log_stage(f"emit:{content.path}", verbosity=ctx.args.verbose)
        options = cmake_emitter.EmitOptions(
            dry_run=ctx.args.dry_run,
            packaging=ctx.config.packaging_enabled,
            namespace=ctx.config.namespace or (ctx.config.project_name or DEFAULT_PROJECT_NAME),
        )
        emit_result = cmake_emitter.emit(
            ir_result.project,
            ctx.args.output_dir,
            options=options,
            fs=ctx.filesystem,
            diagnostics=ctx.diagnostics,
            unknown_factory=ctx.unknown_factory,
        )
        if emit_result.unknown_constructs:
            ctx.unknown_constructs.extend(emit_result.unknown_constructs)


def _serialize_diagnostics(diagnostics: DiagnosticCollector) -> list[dict]:
    """Serialize diagnostics to JSON-compatible format."""
    return [
        {
            "severity": d.severity,
            "code": d.code,
            "message": d.message,
            "location": d.location,
            "origin": d.origin,
        }
        for d in diagnostics.diagnostics
    ]


def _write_report(
    output_dir: Path,
    diagnostics: DiagnosticCollector,
    fs: FileSystemAdapter,
    unknowns: list[UnknownConstruct],
    *,
    project_name: str,
) -> None:
    report_path = output_dir / REPORT_JSON_FILENAME
    markdown_path = output_dir / REPORT_MD_FILENAME
    diag_payload = _serialize_diagnostics(diagnostics)
    unknown_payload = [unknown_to_dict(u) for u in unknowns]
    json_report = {"diagnostics": diag_payload, "unknown_constructs": unknown_payload}
    reporter = MarkdownReporter(project_name)
    markdown = reporter.generate_report(diagnostics, unknowns)
    try:
        fs.makedirs(report_path.parent)
        fs.write_text(report_path, json.dumps(json_report, sort_keys=True))
        fs.write_text(markdown_path, markdown)
    except (IOError, OSError) as exc:  # pragma: no cover - IO error path
        add(diagnostics, "ERROR", "REPORT_WRITE_FAIL", f"Failed to write report: {exc}")
    except (TypeError, ValueError) as exc:  # pragma: no cover - serialization error path
        add(diagnostics, "ERROR", "REPORT_SERIALIZE_FAIL", f"Failed to serialize report: {exc}")


def _stdout() -> TextIO:
    """Return the standard output stream.

    Returns:
        sys.stdout as a TextIO stream for output operations.
    """
    return sys.stdout


def main() -> None:
    code = run(sys.argv[1:])
    raise SystemExit(code)
