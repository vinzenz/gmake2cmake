"""Exit code strategy for gmake2cmake CLI.

Defines a mapping of diagnostic categories to specific exit codes
to provide better information about failure causes.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gmake2cmake.diagnostics import DiagnosticCollector


class ExitCode(IntEnum):
    """Exit codes for gmake2cmake CLI.

    Success:
        0: Successful execution with no errors

    Failure categories:
        1: Usage/CLI error (invalid arguments, unhandled exceptions)
        2: Configuration error (missing, unreadable, or invalid config)
        3: Parse error (Makefile parsing failures)
        4: Build/IR error (IR builder, target mapping, dependency issues)
        5: IO/Emit error (file write failures, output generation issues)
    """

    SUCCESS = 0
    USAGE = 1
    CONFIG = 2
    PARSE = 3
    BUILD = 4
    IO = 5


# Mapping of diagnostic codes to exit code categories
_CODE_TO_CATEGORY = {
    # Usage/CLI errors
    "CLI_UNHANDLED": ExitCode.USAGE,
    # Config errors
    "CONFIG_MISSING": ExitCode.CONFIG,
    "CONFIG_READ_FAIL": ExitCode.CONFIG,
    "CONFIG_PARSE_ERROR": ExitCode.CONFIG,
    "CONFIG_SCHEMA": ExitCode.CONFIG,
    "CONFIG_SCHEMA_VALIDATION": ExitCode.CONFIG,
    "CONFIG_SCHEMA_ERROR": ExitCode.CONFIG,
    "CONFIG_VALIDATION_ERROR": ExitCode.CONFIG,
    "CONFIG_UNKNOWN_KEY": ExitCode.CONFIG,
    "CONFIG_CUSTOM_RULE_INVALID": ExitCode.CONFIG,
    "CONFIG_LINK_OVERRIDE_INVALID": ExitCode.CONFIG,
    # Parse errors (evaluation phase)
    "EVAL_RECURSIVE_LOOP": ExitCode.PARSE,
    "EVAL_NO_SOURCE": ExitCode.PARSE,
    # IR/Build errors
    "IR_UNMAPPED_FLAG": ExitCode.BUILD,
    "IR_DUP_TARGET": ExitCode.BUILD,
    "IR_DUP_ALIAS": ExitCode.BUILD,
    "IR_NO_PATTERN_MATCHES": ExitCode.BUILD,
    "IR_PATTERN_ERROR": ExitCode.BUILD,
    "IR_DEPENDENCY_CYCLE": ExitCode.BUILD,
    # Discovery errors
    "DISCOVERY_ENTRY_MISSING": ExitCode.CONFIG,
    "DISCOVERY_CYCLE": ExitCode.BUILD,
    "DISCOVERY_READ_FAIL": ExitCode.IO,
    "DISCOVERY_INCLUDE_MISSING": ExitCode.CONFIG,
    "DISCOVERY_INCLUDE_OPTIONAL_MISSING": ExitCode.PARSE,
    "DISCOVERY_SUBDIR_MISSING": ExitCode.CONFIG,
    # IO/Emit errors
    "EMIT_WRITE_FAIL": ExitCode.IO,
    "EMIT_UNKNOWN_TYPE": ExitCode.BUILD,
    "REPORT_WRITE_FAIL": ExitCode.IO,
    "REPORT_SERIALIZE_FAIL": ExitCode.IO,
}


def get_exit_code(collector: DiagnosticCollector) -> int:
    """Derive exit code from collected diagnostics.

    Analyzes all ERROR diagnostics and returns the most critical
    exit code category. If no errors exist, returns SUCCESS (0).

    Args:
        collector: DiagnosticCollector instance containing diagnostics

    Returns:
        ExitCode integer (0-5) indicating the failure category
    """
    error_codes = {
        d.code for d in collector.diagnostics
        if d.severity == "ERROR"
    }

    if not error_codes:
        return ExitCode.SUCCESS

    # Find the highest priority exit code
    categories = {
        _CODE_TO_CATEGORY.get(code, ExitCode.USAGE)
        for code in error_codes
    }

    # If multiple categories, prioritize by severity:
    # CONFIG (2) > IO (5) > BUILD (4) > PARSE (3) > USAGE (1)
    if ExitCode.CONFIG in categories:
        return ExitCode.CONFIG
    if ExitCode.IO in categories:
        return ExitCode.IO
    if ExitCode.BUILD in categories:
        return ExitCode.BUILD
    if ExitCode.PARSE in categories:
        return ExitCode.PARSE
    if ExitCode.USAGE in categories:
        return ExitCode.USAGE

    return ExitCode.USAGE


def get_exit_code_with_unknown_threshold(
    collector: DiagnosticCollector,
    unknown_count: int,
    threshold: int = 0,
) -> int:
    """Derive exit code considering both diagnostics and unknown construct count.

    If unknown constructs exceed the threshold, returns PARSE exit code
    to indicate significant unknown constructs that may affect correctness.

    Args:
        collector: DiagnosticCollector instance containing diagnostics
        unknown_count: Number of unknown constructs found
        threshold: Threshold above which unknown count triggers PARSE exit code

    Returns:
        ExitCode integer (0-5) indicating the failure category
    """
    code = get_exit_code(collector)

    # If we have an error already, return that
    if code != ExitCode.SUCCESS:
        return code

    # Check unknown construct threshold
    if threshold > 0 and unknown_count > threshold:
        return ExitCode.PARSE

    return ExitCode.SUCCESS
