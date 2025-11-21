# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using gmake2cmake.

## Installation Issues

### "Command not found: gmake2cmake"

**Symptoms:**
```bash
$ gmake2cmake
bash: gmake2cmake: command not found
```

**Cause:** gmake2cmake is not installed or not in PATH.

**Solution:**

1. Install gmake2cmake:
   ```bash
   pip install gmake2cmake
   ```

2. Verify installation:
   ```bash
   which gmake2cmake
   gmake2cmake --version
   ```

3. If installed but not in PATH, add to PATH:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

4. For virtual environment installations:
   ```bash
   source venv/bin/activate
   gmake2cmake --version
   ```

### "ImportError: No module named gmake2cmake"

**Symptoms:**
```
ImportError: No module named 'gmake2cmake'
```

**Cause:** Python cannot find gmake2cmake module.

**Solution:**

1. Ensure correct Python environment:
   ```bash
   which python
   python --version
   ```

2. Reinstall in correct environment:
   ```bash
   pip install --upgrade gmake2cmake
   ```

3. Verify installation:
   ```bash
   python -c "import gmake2cmake; print(gmake2cmake.__version__)"
   ```

---

## Configuration Issues

### "Configuration file not found"

**Symptoms:**
```
Error: Configuration file 'gmake2cmake.yaml' not found
```

**Cause:** Configuration file doesn't exist or path is incorrect.

**Solution:**

1. Verify file exists:
   ```bash
   ls -la gmake2cmake.yaml
   ```

2. Check current directory:
   ```bash
   pwd
   ```

3. Use absolute path:
   ```bash
   gmake2cmake --config /absolute/path/to/gmake2cmake.yaml
   ```

4. Create default configuration:
   ```bash
   gmake2cmake --generate-config > gmake2cmake.yaml
   ```

### "Invalid YAML format"

**Symptoms:**
```
Error: Invalid YAML in configuration file
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Cause:** YAML syntax error (usually indentation or special characters).

**Solution:**

1. Validate YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('gmake2cmake.yaml'))"
   ```

2. Common YAML errors:

   **Wrong (mixed tabs and spaces):**
   ```yaml
   output:
   	directory: "build"  # Tab character
       overwrite: false    # Spaces
   ```

   **Correct (consistent spaces):**
   ```yaml
   output:
     directory: "build"
     overwrite: false
   ```

3. Quote special characters:

   **Wrong:**
   ```yaml
   variables:
     CFLAGS: -Wall -O2: optimize
   ```

   **Correct:**
   ```yaml
   variables:
     CFLAGS: "-Wall -O2: optimize"
   ```

4. Use online YAML validator: https://www.yamllint.com/

### "Unknown configuration option"

**Symptoms:**
```
Warning: Unknown configuration option 'ouput' (did you mean 'output'?)
```

**Cause:** Typo in configuration key name.

**Solution:**

1. Check spelling against documentation
2. Use `--validate-config` to check before running:
   ```bash
   gmake2cmake --config gmake2cmake.yaml --validate-config
   ```

3. Common typos:
   - `ouput` → `output`
   - `makfile` → `makefile`
   - `diagostics` → `diagnostics`

---

## Makefile Parsing Issues

### "Failed to parse Makefile"

**Symptoms:**
```
Error: Failed to parse Makefile at line 42: unexpected token
```

**Cause:** Makefile contains syntax that gmake2cmake doesn't understand.

**Solution:**

1. Check Makefile syntax:
   ```bash
   make -n  # Dry-run with GNU Make
   ```

2. Enable debug logging:
   ```bash
   GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake -vvv
   ```

3. Common problematic constructs:

   **Complex shell commands in rules:**
   ```makefile
   # May cause issues
   target:
   	for i in $$list; do \
   		if [ -f $$i ]; then echo $$i; fi \
   	done
   ```

   **Solution:** Simplify or use shell script:
   ```makefile
   target:
   	./scripts/process_files.sh
   ```

4. Check for GNU Make extensions:
   - `$(eval ...)` - Runtime evaluation
   - `$(call ...)` - Complex function calls
   - `define ... endef` - Multi-line variable definitions

5. Generate diagnostic report:
   ```bash
   gmake2cmake --config gmake2cmake.yaml --diagnostics markdown > report.md
   ```

### "Unsupported Makefile feature"

**Symptoms:**
```
Warning: Unsupported feature 'eval' at line 15
```

**Cause:** Makefile uses advanced GNU Make features not yet supported.

**Solution:**

1. Check diagnostic report for details
2. Common unsupported features:
   - Runtime `eval`
   - Complex `foreach` with nested expansions
   - Automatic variables in unusual contexts
   - Advanced pattern matching

3. Workarounds:

   **Original (unsupported):**
   ```makefile
   $(eval SOURCES += generated_$(TARGET).c)
   ```

   **Workaround (pre-define):**
   ```makefile
   SOURCES = main.c utils.c generated_myapp.c
   ```

4. File issue for enhancement: Include Makefile snippet and expected CMake output

### "Circular dependency detected"

**Symptoms:**
```
Error: Circular dependency detected: target_a -> target_b -> target_a
```

**Cause:** Makefile contains circular dependencies between targets.

**Solution:**

1. Review dependency chain in diagnostic report
2. Fix Makefile to remove circular dependencies:

   **Wrong:**
   ```makefile
   a: b
   	echo "Building a"

   b: a
   	echo "Building b"
   ```

   **Correct:**
   ```makefile
   all: a b

   a:
   	echo "Building a"

   b:
   	echo "Building b"
   ```

3. Use `--ignore-circular-deps` flag (not recommended):
   ```bash
   gmake2cmake --ignore-circular-deps
   ```

---

## Variable Expansion Issues

### "Undefined variable"

**Symptoms:**
```
Warning: Reference to undefined variable 'CC' at line 10
```

**Cause:** Makefile references variable that's not defined.

**Solution:**

1. Define variable in configuration:
   ```yaml
   variables:
     CC: "gcc"
     CXX: "g++"
     CFLAGS: "-Wall -O2"
   ```

2. Check if variable is from environment:
   ```bash
   echo $CC
   export CC=gcc
   gmake2cmake
   ```

3. Let Make define default:
   ```yaml
   diagnostics:
     suppress:
       - "UNDEFINED_VARIABLE"
   ```

### "Variable recursion detected"

**Symptoms:**
```
Error: Variable recursion detected: CFLAGS references itself
```

**Cause:** Variable definition references itself in a loop.

**Solution:**

**Wrong:**
```makefile
CFLAGS = $(CFLAGS) -Wall
```

**Correct:**
```makefile
CFLAGS := $(CFLAGS) -Wall  # Use := for immediate expansion
```

Or define in configuration:
```yaml
variables:
  CFLAGS: "-Wall -O2"
```

---

## CMake Generation Issues

### "Failed to generate CMakeLists.txt"

**Symptoms:**
```
Error: Failed to write CMakeLists.txt: Permission denied
```

**Cause:** No write permission for output directory.

**Solution:**

1. Check directory permissions:
   ```bash
   ls -ld .
   ```

2. Change permissions:
   ```bash
   chmod u+w .
   ```

3. Use different output directory:
   ```yaml
   output:
     directory: "cmake_output"
   ```

### "Generated CMakeLists.txt doesn't work"

**Symptoms:**
```bash
$ cmake .
CMake Error at CMakeLists.txt:15 (add_executable):
  Cannot find source file: generated.c
```

**Cause:** Generated CMake doesn't handle all Makefile complexities.

**Solution:**

1. Review generated CMakeLists.txt
2. Check diagnostic report for warnings
3. Common issues:

   **Generated files not handled:**
   - Add custom commands manually
   - Use `add_custom_command()` for code generation

   **Example:**
   ```cmake
   add_custom_command(
       OUTPUT generated.c
       COMMAND codegen ${CMAKE_CURRENT_SOURCE_DIR}/input.def > generated.c
       DEPENDS codegen input.def
   )
   ```

4. Platform-specific paths:

   **Wrong:**
   ```cmake
   target_include_directories(myapp PRIVATE /usr/local/include)
   ```

   **Correct:**
   ```cmake
   find_path(MYLIB_INCLUDE_DIR mylib.h)
   target_include_directories(myapp PRIVATE ${MYLIB_INCLUDE_DIR})
   ```

### "CMake finds wrong libraries"

**Symptoms:**
```
CMake Error: Could not find library: mylib
```

**Cause:** Library search paths not correctly translated.

**Solution:**

1. Add library search paths:
   ```cmake
   link_directories(/usr/local/lib)
   ```

2. Use `find_library()`:
   ```cmake
   find_library(MYLIB_LIB mylib PATHS /usr/local/lib)
   target_link_libraries(myapp PRIVATE ${MYLIB_LIB})
   ```

3. Use find modules:
   ```cmake
   find_package(MyLib REQUIRED)
   target_link_libraries(myapp PRIVATE MyLib::MyLib)
   ```

---

## Performance Issues

### "Conversion takes too long"

**Symptoms:**
Conversion of large project takes several minutes.

**Cause:** Large number of Makefiles or complex parsing.

**Solution:**

1. Enable parallel processing:
   ```yaml
   performance:
     parallel: true
     max_workers: 8
   ```

2. Enable caching:
   ```yaml
   performance:
     cache: true
     cache_directory: ".gmake2cmake_cache"
   ```

3. Process incrementally:
   ```bash
   # Process directories separately
   gmake2cmake --config lib.yaml  # Process lib/
   gmake2cmake --config apps.yaml  # Process apps/
   ```

4. Exclude unnecessary Makefiles:
   ```yaml
   makefiles:
     - "Makefile"
     - "lib/Makefile"
     # Don't include test Makefiles during development
   ```

### "High memory usage"

**Symptoms:**
```
MemoryError: Unable to allocate memory
```

**Cause:** Processing very large Makefiles or many files simultaneously.

**Solution:**

1. Reduce parallel workers:
   ```yaml
   performance:
     max_workers: 2  # Reduce from default
   ```

2. Process in batches:
   ```bash
   # Batch 1
   gmake2cmake --makefiles "lib/*/Makefile"

   # Batch 2
   gmake2cmake --makefiles "apps/*/Makefile"
   ```

3. Increase system limits:
   ```bash
   ulimit -v unlimited  # Remove virtual memory limit
   ```

---

## Diagnostic and Logging Issues

### "Too many warnings"

**Symptoms:**
Hundreds of warnings making output unreadable.

**Cause:** Diagnostic level set too low or many minor issues.

**Solution:**

1. Increase diagnostic level:
   ```yaml
   diagnostics:
     level: "error"  # Only show errors
   ```

2. Suppress specific warnings:
   ```yaml
   diagnostics:
     suppress:
       - "UNKNOWN_FUNCTION"
       - "SHELL_COMMAND"
       - "MISSING_DEPENDENCY"
   ```

3. Output to file:
   ```yaml
   diagnostics:
     format: "markdown"
     output: "warnings.md"
   ```

### "Debug output not showing"

**Symptoms:**
`-vvv` or `GMAKE2CMAKE_LOG_LEVEL=DEBUG` doesn't emit debug messages.

**Cause:** Logging configuration issue.

**Solution:**

1. Verify log level:
   ```bash
   GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake -vvv 2>&1 | head
   ```

2. Check for log file redirection:
   ```bash
   GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake -vvv --log-file debug.log
   cat debug.log
   ```

3. Verify no configuration override:
   ```yaml
   # Remove or comment out:
   # logging:
   #   level: "warning"
   ```

---

## Integration Issues

### "CMake version incompatibility"

**Symptoms:**
```
CMake Error: CMake 3.10 or higher is required.  You are running version 2.8.12
```

**Cause:** Generated CMakeLists.txt requires newer CMake than available.

**Solution:**

1. Update CMake:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install cmake

   # Using pip
   pip install cmake

   # From source
   wget https://github.com/Kitware/CMake/releases/download/v3.25.0/cmake-3.25.0.tar.gz
   ```

2. Lower minimum version in configuration:
   ```yaml
   cmake_minimum_version: "3.5"  # Lower requirement
   ```

3. Remove features requiring newer CMake in generated files

### "Build fails with generated CMakeLists.txt"

**Symptoms:**
```bash
$ cmake --build .
ninja: error: 'lib/libcore.a', needed by 'myapp', missing and no known rule to make it
```

**Cause:** Dependency order not correctly determined.

**Solution:**

1. Check target dependencies in CMakeLists.txt:
   ```cmake
   add_dependencies(myapp core)  # Ensure core is built first
   ```

2. Review build order in diagnostic report
3. Manually adjust `add_subdirectory()` order
4. Use explicit dependencies:
   ```cmake
   add_subdirectory(lib/core)
   add_subdirectory(lib/utils)
   add_subdirectory(apps)  # After libraries
   ```

---

## Getting Help

### Gather Diagnostic Information

When reporting issues, include:

1. **Version information:**
   ```bash
   gmake2cmake --version
   python --version
   make --version
   cmake --version
   ```

2. **Configuration file:**
   ```bash
   cat gmake2cmake.yaml
   ```

3. **Minimal Makefile reproducing issue:**
   ```bash
   cat Makefile
   ```

5. **Template Makefiles (autotools/openssl-style):**
   ```bash
   ls Makefile.in Makefile.tpl Makefile.def
   # If only templates exist, run ./configure or ./Configure to generate Makefile
   ```

4. **Debug output:**
   ```bash
   GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake -vvv --log-file debug.log
   ```

5. **Diagnostic report:**
   ```bash
   gmake2cmake --diagnostics markdown > report.md
   ```

### Report Issues

File issues at: https://github.com/your-org/gmake2cmake/issues

Include:
- Clear description of problem
- Expected vs actual behavior
- Diagnostic information above
- Minimal reproducible example

### Community Support

- Documentation: https://gmake2cmake.readthedocs.io
- Discussions: https://github.com/your-org/gmake2cmake/discussions
- Stack Overflow: Tag questions with `gmake2cmake`

## See Also

- [Configuration Guide](configuration.md) - Configuration options
- [Use Cases](use_cases.md) - Common scenarios
- [Performance Guide](performance.md) - Optimization tips
