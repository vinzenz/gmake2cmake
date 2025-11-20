"""Configuration schema validation utilities.

Provides JSON schema-based validation for configuration files with
fallback to basic validation if jsonschema library is unavailable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.exceptions import ConfigValidationError, ConfigFileError

logger = logging.getLogger(__name__)

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


def load_schema() -> Dict[str, Any]:
    """Load the JSON schema for configuration.

    Returns:
        Dictionary containing the JSON schema.

    Raises:
        ConfigFileError: If schema file cannot be read or parsed
    """
    schema_path = Path(__file__).parent / "config_schema.json"
    try:
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error("Schema file not found: %s", schema_path)
        raise ConfigFileError(f"Schema file not found: {schema_path}") from e
    except json.JSONDecodeError as e:
        logger.error("Failed to parse schema JSON: %s", e)
        raise ConfigFileError(f"Schema file is not valid JSON: {schema_path}") from e
    except (IOError, OSError) as e:
        logger.error("Error reading schema file: %s", e)
        raise ConfigFileError(f"Cannot read schema file: {schema_path}") from e


def validate_config_schema(config_data: Dict[str, Any], diagnostics: DiagnosticCollector) -> bool:
    """Validate configuration data against schema.

    Args:
        config_data: Configuration dictionary to validate.
        diagnostics: Collector for validation errors.

    Returns:
        True if validation passes, False otherwise.
    """
    if not JSONSCHEMA_AVAILABLE:
        # Fallback to basic validation if jsonschema is not available
        logger.debug("jsonschema not available, using basic validation")
        return _basic_config_validation(config_data, diagnostics)

    try:
        schema = load_schema()
        jsonschema.validate(instance=config_data, schema=schema)
        logger.info("Configuration schema validation passed")
        return True
    except jsonschema.ValidationError as e:
        error_path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        message = f"Invalid configuration at {error_path}: {e.message}"
        logger.error("Schema validation failed: %s", message)
        add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", message)
        return False
    except jsonschema.SchemaError as e:
        logger.error("Schema itself is invalid: %s", e.message)
        add(diagnostics, "ERROR", "CONFIG_SCHEMA_ERROR", f"Schema error: {e.message}")
        return False
    except ConfigFileError as e:
        # ConfigFileError from load_schema()
        logger.error("Failed to load schema: %s", e)
        add(diagnostics, "ERROR", "CONFIG_FILE_ERROR", str(e))
        return False
    except (TypeError, ValueError) as e:
        # Data structure errors
        logger.error("Configuration data type error: %s", e)
        add(diagnostics, "ERROR", "CONFIG_TYPE_ERROR", f"Configuration type error: {e}")
        return False


def _basic_config_validation(config_data: Dict[str, Any], diagnostics: DiagnosticCollector) -> bool:
    """Basic configuration validation without jsonschema.

    Args:
        config_data: Configuration dictionary to validate.
        diagnostics: Collector for validation errors.

    Returns:
        True if basic validation passes, False otherwise.
    """
    valid_keys = {
        "project_name",
        "version",
        "namespace",
        "languages",
        "target_mappings",
        "flag_mappings",
        "ignore_paths",
        "custom_rules",
        "global_config_files",
        "link_overrides",
        "packaging_enabled",
        "strict",
        "error_recovery_enabled",
    }

    # Check for unknown keys
    for key in config_data.keys():
        if key not in valid_keys:
            add(diagnostics, "WARN", "CONFIG_UNKNOWN_KEY", f"Unknown config key: {key}")

    # Validate project_name type
    if "project_name" in config_data and not isinstance(config_data["project_name"], (str, type(None))):
        add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", "project_name must be a string")
        return False

    # Validate languages type
    if "languages" in config_data:
        langs = config_data["languages"]
        if not isinstance(langs, list):
            add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", "languages must be a list")
            return False
        for lang in langs:
            if lang not in {"C", "CXX", "ASM", "RC"}:
                add(diagnostics, "WARN", "CONFIG_SCHEMA_VALIDATION", f"Unknown language: {lang}")

    # Validate dictionaries
    for dict_key in ["target_mappings", "flag_mappings", "custom_rules", "link_overrides"]:
        if dict_key in config_data:
            value = config_data[dict_key]
            if not isinstance(value, dict):
                add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", f"{dict_key} must be a dictionary")
                return False

    # Validate lists
    for list_key in ["ignore_paths", "global_config_files"]:
        if list_key in config_data:
            value = config_data[list_key]
            if not isinstance(value, list):
                add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", f"{list_key} must be a list")
                return False

    # Validate booleans
    for bool_key in ["packaging_enabled", "strict", "error_recovery_enabled"]:
        if bool_key in config_data:
            value = config_data[bool_key]
            if not isinstance(value, bool):
                add(diagnostics, "ERROR", "CONFIG_SCHEMA_VALIDATION", f"{bool_key} must be a boolean")
                return False

    return True


def generate_config_template() -> str:
    """Generate a sample configuration file with documentation.

    Returns:
        Markdown-formatted configuration template with explanations.
    """
    template = """# gmake2cmake Configuration Template

This is a sample configuration file for gmake2cmake conversion.

## Basic Project Settings

```yaml
# Project name for CMake
project_name: my_project

# Project version (optional)
version: 1.0.0

# C++ namespace (optional, derived from project_name if not set)
namespace: MyProject

# Programming languages to enable
languages:
  - C
  - CXX
```

## Flag Mapping

Map Make compiler flags to CMake-compatible equivalents:

```yaml
flag_mappings:
  -O2: -O3
  -Wall: -Wextra
```

## Path Handling

Paths to ignore during Make discovery:

```yaml
ignore_paths:
  - build/
  - .git/
  - vendor/
```

## Target Configuration

Configure specific Make targets:

```yaml
target_mappings:
  mylib:
    dest_name: MyLib
    type_override: library
    include_dirs:
      - src/include
    defines:
      - ENABLE_FEATURE
    options:
      - POSITION_INDEPENDENT_CODE ON
    visibility: PUBLIC
```

## Library Overrides

Classify external or imported libraries:

```yaml
link_overrides:
  libz:
    classification: imported
    imported_target: ZLIB::ZLIB
  boost:
    classification: external
```

## Build Configuration

Additional configuration:

```yaml
# Generate install/package CMake files
packaging_enabled: false

# Strict mode: treat unknown config keys as errors
strict: false

# Enable error recovery during conversion
error_recovery_enabled: true
```

## Custom Rules (Advanced)

Define custom rule handlers:

```yaml
custom_rules:
  my_rule:
    match: "my_pattern"
    handler: "mypackage.handlers.my_handler"
    cmake_stub: |
      message(STATUS "Custom rule handled")
```

## Global Config Files

Files to scan for global configuration (Make variables, etc.):

```yaml
global_config_files:
  - config.mk
  - rules.mk
  - defs.mk
```
"""
    return template
