# Configuration Guide

## Overview

The gmake2cmake configuration system provides flexible control over the Makefile-to-CMake conversion process. Configuration can be specified through YAML or JSON files, allowing you to customize target handling, variable mapping, and output generation.

## Configuration File Format

gmake2cmake supports both YAML and JSON configuration files. The default configuration file name is `gmake2cmake.yaml` or `gmake2cmake.json`.

### Basic Configuration Example

```yaml
# gmake2cmake.yaml
project_name: "MyProject"
cmake_minimum_version: "3.15"

output:
  directory: "build"
  overwrite: false

makefiles:
  - "Makefile"
  - "src/Makefile"

variables:
  CC: "gcc"
  CFLAGS: "-Wall -O2"
```

### JSON Format

```json
{
  "project_name": "MyProject",
  "cmake_minimum_version": "3.15",
  "output": {
    "directory": "build",
    "overwrite": false
  },
  "makefiles": [
    "Makefile",
    "src/Makefile"
  ],
  "variables": {
    "CC": "gcc",
    "CFLAGS": "-Wall -O2"
  }
}
```

## Configuration Options

### Project Settings

#### `project_name` (string, required)
Name of the CMake project. This will be used in the `project()` command.

**Example:**
```yaml
project_name: "MyAwesomeProject"
```

**Generated CMake:**
```cmake
project(MyAwesomeProject)
```

#### `cmake_minimum_version` (string, optional)
Minimum CMake version required. Default: `"3.10"`

**Example:**
```yaml
cmake_minimum_version: "3.20"
```

**Generated CMake:**
```cmake
cmake_minimum_required(VERSION 3.20)
```

#### `languages` (list, optional)
Programming languages used in the project. Default: `["C", "CXX"]`

**Example:**
```yaml
languages:
  - C
  - CXX
  - Fortran
```

### Output Settings

#### `output.directory` (string, optional)
Directory where generated CMakeLists.txt files will be written. Default: `"."`

**Example:**
```yaml
output:
  directory: "cmake"
```

#### `output.overwrite` (boolean, optional)
Whether to overwrite existing CMakeLists.txt files. Default: `false`

**Example:**
```yaml
output:
  overwrite: true
```

**Warning:** Setting `overwrite: true` will replace existing CMakeLists.txt files without warning.

#### `output.format` (string, optional)
Output format style. Options: `"readable"`, `"compact"`. Default: `"readable"`

**Example:**
```yaml
output:
  format: "readable"
```

### Input Settings

#### `makefiles` (list, required)
List of Makefile paths to process.

**Example:**
```yaml
makefiles:
  - "Makefile"
  - "src/Makefile"
  - "tests/Makefile"
```

**Relative vs Absolute Paths:**
- Relative paths are resolved from the configuration file directory
- Absolute paths are used as-is

#### `include_directories` (list, optional)
Additional directories to search for included Makefiles.

**Example:**
```yaml
include_directories:
  - "make"
  - "build/generated"
```

### Variable Configuration

#### `variables` (object, optional)
Predefined Make variables to use during evaluation.

**Example:**
```yaml
variables:
  CC: "gcc"
  CXX: "g++"
  CFLAGS: "-Wall -Wextra -O2"
  LDFLAGS: "-lpthread"
  PREFIX: "/usr/local"
```

**Variable Expansion:**
Variables can reference other variables using Make syntax:
```yaml
variables:
  SRCDIR: "src"
  INCDIR: "$(SRCDIR)/include"
```

#### `variable_mappings` (object, optional)
Map Make variables to CMake variables or properties.

**Example:**
```yaml
variable_mappings:
  CFLAGS: "CMAKE_C_FLAGS"
  CXXFLAGS: "CMAKE_CXX_FLAGS"
  LDFLAGS: "CMAKE_EXE_LINKER_FLAGS"
```

### Target Configuration

#### `targets.exclude` (list, optional)
List of target names or patterns to exclude from conversion.

**Example:**
```yaml
targets:
  exclude:
    - "clean"
    - "distclean"
    - "*.tmp"
```

#### `targets.library_type` (string, optional)
Default library type for targets. Options: `"STATIC"`, `"SHARED"`, `"MODULE"`. Default: `"STATIC"`

**Example:**
```yaml
targets:
  library_type: "SHARED"
```

#### `targets.executable_suffix` (string, optional)
Suffix to add to executable targets.

**Example:**
```yaml
targets:
  executable_suffix: ".exe"
```

### Diagnostic Settings

#### `diagnostics.level` (string, optional)
Minimum diagnostic level to report. Options: `"error"`, `"warning"`, `"info"`, `"hint"`. Default: `"warning"`

**Example:**
```yaml
diagnostics:
  level: "info"
```

#### `diagnostics.format` (string, optional)
Diagnostic output format. Options: `"text"`, `"json"`, `"markdown"`. Default: `"text"`

**Example:**
```yaml
diagnostics:
  format: "markdown"
  output: "diagnostics.md"
```

#### `diagnostics.suppress` (list, optional)
List of diagnostic codes to suppress.

**Example:**
```yaml
diagnostics:
  suppress:
    - "UNKNOWN_FUNCTION"
    - "MISSING_DEPENDENCY"
```

### Performance Settings

#### `performance.parallel` (boolean, optional)
Enable parallel processing of Makefiles. Default: `true`

**Example:**
```yaml
performance:
  parallel: true
  max_workers: 4
```

#### `performance.cache` (boolean, optional)
Enable caching of parsed Makefiles. Default: `true`

**Example:**
```yaml
performance:
  cache: true
  cache_directory: ".gmake2cmake_cache"
```

## Complete Configuration Example

```yaml
# gmake2cmake.yaml - Complete Configuration Example
project_name: "ComplexProject"
cmake_minimum_version: "3.18"
languages:
  - C
  - CXX

output:
  directory: "cmake"
  overwrite: false
  format: "readable"

makefiles:
  - "Makefile"
  - "src/Makefile"
  - "lib/Makefile"
  - "tests/Makefile"

include_directories:
  - "make"
  - "build"

variables:
  CC: "gcc"
  CXX: "g++"
  CFLAGS: "-Wall -Wextra -O2 -g"
  CXXFLAGS: "-Wall -Wextra -O2 -g -std=c++17"
  LDFLAGS: "-lpthread -lm"
  PREFIX: "/usr/local"
  SRCDIR: "src"
  BUILDDIR: "build"

variable_mappings:
  CFLAGS: "CMAKE_C_FLAGS"
  CXXFLAGS: "CMAKE_CXX_FLAGS"
  LDFLAGS: "CMAKE_EXE_LINKER_FLAGS"
  PREFIX: "CMAKE_INSTALL_PREFIX"

targets:
  exclude:
    - "clean"
    - "distclean"
    - "install"
    - "*.tmp"
  library_type: "SHARED"
  executable_suffix: ""

diagnostics:
  level: "warning"
  format: "markdown"
  output: "conversion_report.md"
  suppress:
    - "UNKNOWN_FUNCTION"

performance:
  parallel: true
  max_workers: 4
  cache: true
  cache_directory: ".gmake2cmake_cache"
```

## Default Values

If no configuration file is provided, gmake2cmake uses these defaults:

```yaml
project_name: "Project"
cmake_minimum_version: "3.10"
languages: ["C", "CXX"]

output:
  directory: "."
  overwrite: false
  format: "readable"

makefiles: ["Makefile"]

diagnostics:
  level: "warning"
  format: "text"

performance:
  parallel: true
  cache: true
```

## Configuration Loading Order

gmake2cmake searches for configuration files in this order:

1. Command-line specified config file (`--config`)
2. `gmake2cmake.yaml` in current directory
3. `gmake2cmake.json` in current directory
4. `.gmake2cmake.yaml` in home directory
5. `.gmake2cmake.json` in home directory
6. Default configuration

## Troubleshooting Configuration Issues

### "Configuration file not found"

**Cause:** Configuration file path is incorrect or file doesn't exist.

**Solution:**
- Verify the file path is correct
- Use absolute paths if needed
- Check file permissions
- Ensure file extension is `.yaml` or `.json`

### "Invalid configuration format"

**Cause:** YAML or JSON syntax error.

**Solution:**
- Validate YAML syntax using online validator
- Check for proper indentation (YAML is indent-sensitive)
- Ensure all quotes are properly closed
- Validate JSON with a JSON linter

### "Unknown configuration option"

**Cause:** Configuration contains unsupported option.

**Solution:**
- Check option name spelling
- Refer to this guide for valid options
- Remove or comment out unknown options
- Check gmake2cmake version compatibility

### Configuration Not Applied

**Cause:** Configuration file not being loaded.

**Solution:**
- Verify file name matches expected pattern
- Check file is in correct directory
- Use `--config` flag to explicitly specify file
- Increase verbosity with `-vvv` or `GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake ...`

## Logging and tracing

- Logs are JSON-formatted and include correlation IDs. Override the ID with `GMAKE2CMAKE_CORRELATION_ID=...`.
- Control verbosity with `-v/-vv/-vvv` or `GMAKE2CMAKE_LOG_LEVEL` (`DEBUG`, `INFO`, etc.).
- Write logs to disk with `--log-file`; rotate by size/time via `--log-max-bytes`, `--log-backup-count`, `--log-rotate-when`, and `--log-rotate-interval`.
- Send logs to syslog with `--syslog-address /dev/log` (Unix socket) or `--syslog-address host:514` (UDP).
- Stage timings are emitted when verbosity is `-v` or higher; use `-vv` for start/stop markers.

## Configuration Validation

Use the `--validate-config` flag to check configuration without running conversion:

```bash
gmake2cmake --config gmake2cmake.yaml --validate-config
```

This will report any configuration errors without processing Makefiles.

## Environment Variable Expansion

Configuration values can reference environment variables:

```yaml
output:
  directory: "${BUILD_DIR}/cmake"

variables:
  PREFIX: "${INSTALL_PREFIX:-/usr/local}"
```

The syntax `${VAR:-default}` provides a default value if the environment variable is not set.

## Configuration Profiles

You can maintain multiple configuration files for different scenarios:

```bash
# Development build
gmake2cmake --config gmake2cmake.dev.yaml

# Release build
gmake2cmake --config gmake2cmake.release.yaml

# Cross-compilation
gmake2cmake --config gmake2cmake.cross.yaml
```

## See Also

- [Use Cases Guide](use_cases.md) - Common configuration scenarios
- [Troubleshooting Guide](troubleshooting.md) - Solving common problems
- [API Reference](api/config.md) - Configuration API documentation
