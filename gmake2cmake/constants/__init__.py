"""Centralized constants and default values for gmake2cmake.

This package holds all hardcoded defaults, file paths, and configuration
values to keep them in a single, documented location.
"""

from __future__ import annotations

# CLI Defaults
DEFAULT_SOURCE_DIR = "."
DEFAULT_OUTPUT_DIR = "./cmake-out"

# Report file names
REPORT_JSON_FILENAME = "report.json"
# Markdown reporter output filename
REPORT_MD_FILENAME = "report.md"

# Default project name
DEFAULT_PROJECT_NAME = "Project"

# Unknown construct defaults
UNKNOWN_CONSTRUCT_PHASE_PARSE = "parse"
UNKNOWN_CONSTRUCT_SEVERITY_WARNING = "warning"
UNKNOWN_CONSTRUCT_CATEGORY_MAKE_SYNTAX = "make_syntax"
UNKNOWN_CONSTRUCT_SUGGESTED_ACTION_MANUAL_REVIEW = "manual_review"

# Valid types and classifications
# Config allows None for type_override (means no override)
VALID_CONFIG_TARGET_TYPES = {
    "static",
    "shared",
    "object",
    "executable",
    "imported",
    "interface",
    None,
}

# IR Target type must be one of these (never None)
VALID_TARGET_TYPES = {
    "static",
    "shared",
    "object",
    "executable",
    "imported",
    "interface",
}

VALID_VISIBILITY_LEVELS = {"PUBLIC", "PRIVATE", "INTERFACE", None}

VALID_LINK_CLASSIFICATIONS = {"internal", "external", "imported"}

VALID_CMAKE_STATUSES = {
    "not_generated",
    "generated",
    "partial",
}

VALID_SUGGESTED_ACTIONS = {
    "manual_review",
    "auto_fixed",
    "skip",
}

VALID_DIAGNOSTIC_SEVERITIES = {"ERROR", "WARN", "INFO"}

# Default config file locations (for future use)
GLOBAL_CONFIG_FILENAMES = [".gmake2cmake.yaml", "gmake2cmake.yaml"]

__all__ = [
    "DEFAULT_SOURCE_DIR",
    "DEFAULT_OUTPUT_DIR",
    "REPORT_JSON_FILENAME",
    "REPORT_MD_FILENAME",
    "DEFAULT_PROJECT_NAME",
    "UNKNOWN_CONSTRUCT_PHASE_PARSE",
    "UNKNOWN_CONSTRUCT_SEVERITY_WARNING",
    "UNKNOWN_CONSTRUCT_CATEGORY_MAKE_SYNTAX",
    "UNKNOWN_CONSTRUCT_SUGGESTED_ACTION_MANUAL_REVIEW",
    "VALID_CONFIG_TARGET_TYPES",
    "VALID_TARGET_TYPES",
    "VALID_VISIBILITY_LEVELS",
    "VALID_LINK_CLASSIFICATIONS",
    "VALID_CMAKE_STATUSES",
    "VALID_SUGGESTED_ACTIONS",
    "VALID_DIAGNOSTIC_SEVERITIES",
    "GLOBAL_CONFIG_FILENAMES",
]
