"""Registry of diagnostic codes used throughout gmake2cmake.

This module provides a centralized enum of all diagnostic codes with metadata
including severity levels and message templates. All diagnostic codes must be
registered here before use.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class DiagnosticMetadata:
    """Metadata associated with a diagnostic code.

    Attributes:
        code: The diagnostic code string (e.g., 'CONFIG_MISSING')
        category: Category grouping (e.g., 'CLI', 'CONFIG', 'DISCOVERY')
        default_severity: Default severity level for this code
        description: Human-readable description of when this code is used
        message_template: Optional template for the message (for consistency)
    """

    code: str
    category: str
    default_severity: str
    description: str
    message_template: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate metadata after initialization."""
        valid_severities = {"ERROR", "WARN", "INFO"}
        if self.default_severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.default_severity}")


class DiagnosticCode(str, Enum):
    """Enumeration of all valid diagnostic codes.

    These codes categorize diagnostics by their source and severity.
    Each code should be used consistently across the codebase.
    """

    # Test-related codes
    TEST = "TEST"

    # CLI-related codes
    CLI_UNHANDLED = "CLI_UNHANDLED"
    REPORT_WRITE_FAIL = "REPORT_WRITE_FAIL"
    REPORT_SERIALIZE_FAIL = "REPORT_SERIALIZE_FAIL"

    # IR builder codes
    IR_UNMAPPED_FLAG = "IR_UNMAPPED_FLAG"
    IR_DUP_TARGET = "IR_DUP_TARGET"
    IR_DUP_ALIAS = "IR_DUP_ALIAS"
    IR_NO_PATTERN_MATCHES = "IR_NO_PATTERN_MATCHES"
    IR_PATTERN_ERROR = "IR_PATTERN_ERROR"
    IR_DEPENDENCY_CYCLE = "IR_DEPENDENCY_CYCLE"

    # Config-related codes
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_READ_FAIL = "CONFIG_READ_FAIL"
    CONFIG_PARSE_ERROR = "CONFIG_PARSE_ERROR"
    CONFIG_SCHEMA = "CONFIG_SCHEMA"
    CONFIG_SCHEMA_VALIDATION = "CONFIG_SCHEMA_VALIDATION"
    CONFIG_SCHEMA_ERROR = "CONFIG_SCHEMA_ERROR"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"
    CONFIG_UNKNOWN_KEY = "CONFIG_UNKNOWN_KEY"
    CONFIG_CUSTOM_RULE_INVALID = "CONFIG_CUSTOM_RULE_INVALID"
    CONFIG_LINK_OVERRIDE_INVALID = "CONFIG_LINK_OVERRIDE_INVALID"

    # CMake emission codes
    EMIT_WRITE_FAIL = "EMIT_WRITE_FAIL"
    EMIT_UNKNOWN_TYPE = "EMIT_UNKNOWN_TYPE"

    # Discovery-related codes
    DISCOVERY_ENTRY_MISSING = "DISCOVERY_ENTRY_MISSING"
    DISCOVERY_CYCLE = "DISCOVERY_CYCLE"
    DISCOVERY_READ_FAIL = "DISCOVERY_READ_FAIL"
    DISCOVERY_INCLUDE_MISSING = "DISCOVERY_INCLUDE_MISSING"
    DISCOVERY_INCLUDE_OPTIONAL_MISSING = "DISCOVERY_INCLUDE_OPTIONAL_MISSING"
    DISCOVERY_SUBDIR_MISSING = "DISCOVERY_SUBDIR_MISSING"
    DISCOVERY_TEMPLATE_ENTRY = "DISCOVERY_TEMPLATE_ENTRY"

    # Evaluation-related codes
    EVAL_RECURSIVE_LOOP = "EVAL_RECURSIVE_LOOP"
    EVAL_NO_SOURCE = "EVAL_NO_SOURCE"
    UNKNOWN_CONSTRUCT = "UNKNOWN_CONSTRUCT"

    # Validation-related codes
    VALIDATION_PATH = "VALIDATION_PATH"
    VALIDATION_IDENTIFIER = "VALIDATION_IDENTIFIER"
    VALIDATION_INVALID_VALUE = "VALIDATION_INVALID_VALUE"
    CONFIG_TOO_LARGE = "CONFIG_TOO_LARGE"
    INTROSPECTION_TIMEOUT = "INTROSPECTION_TIMEOUT"
    INTROSPECTION_FAILED = "INTROSPECTION_FAILED"
    INTROSPECTION_MISMATCH = "INTROSPECTION_MISMATCH"


# Metadata registry for all diagnostic codes
_METADATA_REGISTRY: dict[str, DiagnosticMetadata] = {
    # Test codes
    "TEST": DiagnosticMetadata(
        code="TEST",
        category="TEST",
        default_severity="INFO",
        description="Test diagnostic code",
    ),
    # CLI codes
    "CLI_UNHANDLED": DiagnosticMetadata(
        code="CLI_UNHANDLED",
        category="CLI",
        default_severity="ERROR",
        description="Unhandled exception in CLI",
        message_template="Unhandled exception: {error}",
    ),
    "REPORT_WRITE_FAIL": DiagnosticMetadata(
        code="REPORT_WRITE_FAIL",
        category="CLI",
        default_severity="ERROR",
        description="Failed to write diagnostic report",
        message_template="Failed to write report: {error}",
    ),
    "REPORT_SERIALIZE_FAIL": DiagnosticMetadata(
        code="REPORT_SERIALIZE_FAIL",
        category="CLI",
        default_severity="ERROR",
        description="Failed to serialize report data",
        message_template="Failed to serialize report: {error}",
    ),
    # IR builder codes
    "IR_UNMAPPED_FLAG": DiagnosticMetadata(
        code="IR_UNMAPPED_FLAG",
        category="IR",
        default_severity="WARN",
        description="Compiler flag could not be mapped to CMake",
    ),
    "IR_DUP_TARGET": DiagnosticMetadata(
        code="IR_DUP_TARGET",
        category="IR",
        default_severity="ERROR",
        description="Duplicate target definition",
    ),
    "IR_DUP_ALIAS": DiagnosticMetadata(
        code="IR_DUP_ALIAS",
        category="IR",
        default_severity="ERROR",
        description="Duplicate alias definition",
    ),
    "IR_NO_PATTERN_MATCHES": DiagnosticMetadata(
        code="IR_NO_PATTERN_MATCHES",
        category="IR",
        default_severity="WARN",
        description="No rules matched a pattern",
    ),
    "IR_PATTERN_ERROR": DiagnosticMetadata(
        code="IR_PATTERN_ERROR",
        category="IR",
        default_severity="ERROR",
        description="Error processing pattern rule",
    ),
    "IR_DEPENDENCY_CYCLE": DiagnosticMetadata(
        code="IR_DEPENDENCY_CYCLE",
        category="IR",
        default_severity="ERROR",
        description="Circular dependency detected",
    ),
    # Config codes
    "CONFIG_MISSING": DiagnosticMetadata(
        code="CONFIG_MISSING",
        category="CONFIG",
        default_severity="ERROR",
        description="Configuration file not found",
        message_template="Config file not found: {path}",
    ),
    "CONFIG_READ_FAIL": DiagnosticMetadata(
        code="CONFIG_READ_FAIL",
        category="CONFIG",
        default_severity="ERROR",
        description="Failed to read configuration file",
        message_template="Failed to read config: {error}",
    ),
    "CONFIG_PARSE_ERROR": DiagnosticMetadata(
        code="CONFIG_PARSE_ERROR",
        category="CONFIG",
        default_severity="ERROR",
        description="Invalid YAML syntax in configuration",
        message_template="Invalid YAML: {error}",
    ),
    "CONFIG_SCHEMA": DiagnosticMetadata(
        code="CONFIG_SCHEMA",
        category="CONFIG",
        default_severity="ERROR",
        description="Configuration schema violation",
    ),
    "CONFIG_SCHEMA_VALIDATION": DiagnosticMetadata(
        code="CONFIG_SCHEMA_VALIDATION",
        category="CONFIG",
        default_severity="ERROR",
        description="Configuration validation failed",
    ),
    "CONFIG_SCHEMA_ERROR": DiagnosticMetadata(
        code="CONFIG_SCHEMA_ERROR",
        category="CONFIG",
        default_severity="ERROR",
        description="Schema definition error",
    ),
    "CONFIG_VALIDATION_ERROR": DiagnosticMetadata(
        code="CONFIG_VALIDATION_ERROR",
        category="CONFIG",
        default_severity="ERROR",
        description="Configuration validation error",
    ),
    "CONFIG_UNKNOWN_KEY": DiagnosticMetadata(
        code="CONFIG_UNKNOWN_KEY",
        category="CONFIG",
        default_severity="WARN",
        description="Unknown configuration key",
        message_template="Unknown config key: {key}",
    ),
    "CONFIG_TOO_LARGE": DiagnosticMetadata(
        code="CONFIG_TOO_LARGE",
        category="CONFIG",
        default_severity="ERROR",
        description="Configuration file exceeds allowed size",
    ),
    "CONFIG_CUSTOM_RULE_INVALID": DiagnosticMetadata(
        code="CONFIG_CUSTOM_RULE_INVALID",
        category="CONFIG",
        default_severity="ERROR",
        description="Invalid custom rule configuration",
    ),
    "CONFIG_LINK_OVERRIDE_INVALID": DiagnosticMetadata(
        code="CONFIG_LINK_OVERRIDE_INVALID",
        category="CONFIG",
        default_severity="ERROR",
        description="Invalid link override configuration",
    ),
    # Emission codes
    "EMIT_WRITE_FAIL": DiagnosticMetadata(
        code="EMIT_WRITE_FAIL",
        category="EMIT",
        default_severity="ERROR",
        description="Failed to write generated file",
        message_template="Failed to write {path}: {error}",
    ),
    "EMIT_UNKNOWN_TYPE": DiagnosticMetadata(
        code="EMIT_UNKNOWN_TYPE",
        category="EMIT",
        default_severity="ERROR",
        description="Unknown target type in emission",
        message_template="Unknown target type {type}",
    ),
    # Discovery codes
    "DISCOVERY_ENTRY_MISSING": DiagnosticMetadata(
        code="DISCOVERY_ENTRY_MISSING",
        category="DISCOVERY",
        default_severity="ERROR",
        description="No entry Makefile found",
        message_template="No Makefile found in {path}",
    ),
    "DISCOVERY_CYCLE": DiagnosticMetadata(
        code="DISCOVERY_CYCLE",
        category="DISCOVERY",
        default_severity="ERROR",
        description="Include cycle detected in Makefiles",
        message_template="Include cycle detected: {cycle}",
    ),
    "DISCOVERY_READ_FAIL": DiagnosticMetadata(
        code="DISCOVERY_READ_FAIL",
        category="DISCOVERY",
        default_severity="ERROR",
        description="Failed to read Makefile",
        message_template="Failed to read {path}: {error}",
    ),
    "DISCOVERY_INCLUDE_MISSING": DiagnosticMetadata(
        code="DISCOVERY_INCLUDE_MISSING",
        category="DISCOVERY",
        default_severity="ERROR",
        description="Included Makefile not found",
        message_template="Missing include {include} from {path}",
    ),
    "DISCOVERY_INCLUDE_OPTIONAL_MISSING": DiagnosticMetadata(
        code="DISCOVERY_INCLUDE_OPTIONAL_MISSING",
        category="DISCOVERY",
        default_severity="WARN",
        description="Optional include Makefile not found",
        message_template="Optional include missing {include}",
    ),
    "DISCOVERY_SUBDIR_MISSING": DiagnosticMetadata(
        code="DISCOVERY_SUBDIR_MISSING",
        category="DISCOVERY",
        default_severity="WARN",
        description="Subdirectory Makefile not found",
        message_template="Subdir Makefile missing at {path}",
    ),
    "DISCOVERY_TEMPLATE_ENTRY": DiagnosticMetadata(
        code="DISCOVERY_TEMPLATE_ENTRY",
        category="DISCOVERY",
        default_severity="WARN",
        description="Template Makefile detected without generated Makefile",
        message_template="Template Makefiles found ({templates}); run configure before conversion",
    ),
    # Evaluation codes
    "EVAL_RECURSIVE_LOOP": DiagnosticMetadata(
        code="EVAL_RECURSIVE_LOOP",
        category="EVAL",
        default_severity="ERROR",
        description="Recursive variable or unclosed variable",
        message_template="Recursive variable {var} at {location}",
    ),
    "EVAL_NO_SOURCE": DiagnosticMetadata(
        code="EVAL_NO_SOURCE",
        category="EVAL",
        default_severity="WARN",
        description="Could not infer source for rule",
        message_template="Could not infer source for rule at {location}",
    ),
    "UNKNOWN_CONSTRUCT": DiagnosticMetadata(
        code="UNKNOWN_CONSTRUCT",
        category="EVAL",
        default_severity="WARN",
        description="Unrecognized Makefile construct",
    ),
    # Validation codes
    "VALIDATION_PATH": DiagnosticMetadata(
        code="VALIDATION_PATH",
        category="VALIDATION",
        default_severity="ERROR",
        description="Invalid or unsafe path input",
    ),
    "VALIDATION_IDENTIFIER": DiagnosticMetadata(
        code="VALIDATION_IDENTIFIER",
        category="VALIDATION",
        default_severity="ERROR",
        description="Invalid identifier input",
    ),
    "VALIDATION_INVALID_VALUE": DiagnosticMetadata(
        code="VALIDATION_INVALID_VALUE",
        category="VALIDATION",
        default_severity="ERROR",
        description="Invalid freeform input value",
    ),
    # Introspection codes
    "INTROSPECTION_TIMEOUT": DiagnosticMetadata(
        code="INTROSPECTION_TIMEOUT",
        category="INTROSPECTION",
        default_severity="WARN",
        description="GNU make introspection timed out",
    ),
    "INTROSPECTION_FAILED": DiagnosticMetadata(
        code="INTROSPECTION_FAILED",
        category="INTROSPECTION",
        default_severity="WARN",
        description="GNU make introspection failed",
    ),
    "INTROSPECTION_MISMATCH": DiagnosticMetadata(
        code="INTROSPECTION_MISMATCH",
        category="INTROSPECTION",
        default_severity="WARN",
        description="Differences found between static analysis and introspection",
    ),
}


def _validate_registry() -> None:
    """Validate that all enum values are registered.

    Raises:
        ValueError: If any enum value lacks metadata or duplicates exist.
    """
    enum_codes = {code.value for code in DiagnosticCode}
    registry_codes = set(_METADATA_REGISTRY.keys())

    missing = enum_codes - registry_codes
    if missing:
        raise ValueError(f"Unregistered diagnostic codes: {missing}")

    extra = registry_codes - enum_codes
    if extra:
        raise ValueError(f"Registered codes not in enum: {extra}")

    # Check for duplicate codes in metadata
    codes_seen = set()
    for metadata in _METADATA_REGISTRY.values():
        if metadata.code in codes_seen:
            raise ValueError(f"Duplicate diagnostic code: {metadata.code}")
        codes_seen.add(metadata.code)


def get_metadata(code: str) -> DiagnosticMetadata:
    """Get metadata for a diagnostic code.

    Args:
        code: The diagnostic code string.

    Returns:
        DiagnosticMetadata for the code.

    Raises:
        ValueError: If the code is not registered.
    """
    if code not in _METADATA_REGISTRY:
        raise ValueError(f"Unknown diagnostic code: {code}")
    return _METADATA_REGISTRY[code]


def is_valid_code(code: str) -> bool:
    """Check if a code is valid and registered.

    Args:
        code: The diagnostic code string to validate.

    Returns:
        True if the code is in the registry, False otherwise.
    """
    try:
        DiagnosticCode(code)
        return True
    except ValueError:
        return False


def validate_code(code: str) -> str:
    """Validate a diagnostic code, raising an error if invalid.

    Args:
        code: The diagnostic code to validate.

    Returns:
        The code if valid.

    Raises:
        ValueError: If the code is not in the registry.
    """
    if not is_valid_code(code):
        raise ValueError(f"Invalid diagnostic code: {code}. Must be one of: {', '.join(c.value for c in DiagnosticCode)}")
    return code


def list_codes_by_category() -> dict[str, list[str]]:
    """List all diagnostic codes grouped by category.

    Returns:
        Dictionary mapping category names to lists of codes.
    """
    categories: dict[str, list[str]] = {}
    for metadata in _METADATA_REGISTRY.values():
        if metadata.category not in categories:
            categories[metadata.category] = []
        categories[metadata.category].append(metadata.code)
    return {cat: sorted(codes) for cat, codes in sorted(categories.items())}


def generate_documentation() -> str:
    """Generate markdown documentation of all diagnostic codes.

    Returns:
        Markdown-formatted documentation of all codes.
    """
    lines = [
        "# Diagnostic Codes",
        "",
        "This document lists all diagnostic codes used by gmake2cmake.",
        "",
    ]

    categories = list_codes_by_category()
    for category, codes in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        for code in codes:
            metadata = get_metadata(code)
            lines.append(f"### `{code}`")
            lines.append("")
            lines.append(f"- **Category:** {metadata.category}")
            lines.append(f"- **Default Severity:** {metadata.default_severity}")
            lines.append(f"- **Description:** {metadata.description}")
            if metadata.message_template:
                lines.append(f"- **Message Template:** `{metadata.message_template}`")
            lines.append("")

    return "\n".join(lines)


# Validate registry on module import
_validate_registry()


def __main__() -> int:
    """Entry point for diagnostic code validation and documentation.

    Usage:
        python -m gmake2cmake.diagnostic_codes --validate
        python -m gmake2cmake.diagnostic_codes --docs

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m gmake2cmake.diagnostic_codes [--validate|--docs]")
        return 1

    command = sys.argv[1]

    if command == "--validate":
        try:
            _validate_registry()
            print("Diagnostic code registry validated successfully.")
            print(f"Total codes: {len(list(DiagnosticCode))}")
            categories = list_codes_by_category()
            print(f"Categories: {len(categories)}")
            for category, codes in sorted(categories.items()):
                print(f"  {category}: {len(codes)} codes")
            return 0
        except ValueError as exc:
            print(f"Validation failed: {exc}", file=sys.stderr)
            return 1
    elif command == "--docs":
        doc = generate_documentation()
        print(doc)
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(__main__())
