# Migration Guide

This guide helps you migrate between different versions of gmake2cmake and provides strategies for transitioning projects from Make to CMake.

## Upgrading gmake2cmake

### Version Compatibility Matrix

| gmake2cmake Version | Python Version | CMake Version | Breaking Changes |
|-------------------|----------------|---------------|------------------|
| 1.0.x | 3.7+ | 3.10+ | Initial release |
| 1.1.x | 3.8+ | 3.10+ | Configuration schema updates |
| 1.2.x | 3.8+ | 3.15+ | Parallel processing, caching |
| 2.0.x | 3.9+ | 3.18+ | New IR system, API changes |

### Upgrading from 1.x to 2.x

#### Breaking Changes

1. **Configuration Schema Changes**

   **v1.x Configuration:**
   ```yaml
   project: "MyProject"
   min_cmake_version: "3.10"
   output_dir: "build"
   ```

   **v2.x Configuration:**
   ```yaml
   project_name: "MyProject"  # Changed key name
   cmake_minimum_version: "3.10"  # Changed key name
   output:
     directory: "build"  # Nested structure
     overwrite: false
   ```

   **Migration Script:**
   ```python
   # migrate_config.py
   import yaml

   def migrate_v1_to_v2(old_config):
       new_config = {}

       if 'project' in old_config:
           new_config['project_name'] = old_config['project']

       if 'min_cmake_version' in old_config:
           new_config['cmake_minimum_version'] = old_config['min_cmake_version']

       if 'output_dir' in old_config:
           new_config['output'] = {
               'directory': old_config['output_dir'],
               'overwrite': old_config.get('overwrite', False)
           }

       return new_config

   # Usage
   with open('gmake2cmake.yaml') as f:
       old = yaml.safe_load(f)

   new = migrate_v1_to_v2(old)

   with open('gmake2cmake.yaml', 'w') as f:
       yaml.dump(new, f, default_flow_style=False)
   ```

2. **API Changes**

   **v1.x API:**
   ```python
   from gmake2cmake import convert

   result = convert(
       makefile="Makefile",
       output="CMakeLists.txt",
       project_name="MyProject"
   )
   ```

   **v2.x API:**
   ```python
   from gmake2cmake import Converter
   from gmake2cmake.config import load_config

   config = load_config("gmake2cmake.yaml")
   converter = Converter(config)
   result = converter.convert()
   ```

3. **CLI Changes**

   **v1.x CLI:**
   ```bash
   gmake2cmake --makefile Makefile --output CMakeLists.txt --project MyProject
   ```

   **v2.x CLI:**
   ```bash
   gmake2cmake --config gmake2cmake.yaml
   # OR
   gmake2cmake --makefile Makefile --project-name MyProject
   ```

#### Deprecated Features

The following features are deprecated in v2.x and will be removed in v3.x:

1. **Direct Makefile Processing Without Config**
   ```bash
   # Deprecated
   gmake2cmake Makefile

   # Use instead
   gmake2cmake --config gmake2cmake.yaml
   ```

2. **Legacy Variable Format**
   ```yaml
   # Deprecated
   variables:
     - name: CC
       value: gcc

   # Use instead
   variables:
     CC: "gcc"
   ```

3. **Old Diagnostic Format**
   ```yaml
   # Deprecated
   diagnostics: true

   # Use instead
   diagnostics:
     level: "warning"
     format: "text"
   ```

#### Migration Steps

1. **Backup Current Setup**
   ```bash
   # Backup configuration
   cp gmake2cmake.yaml gmake2cmake.yaml.v1.backup

   # Backup generated CMake files
   cp CMakeLists.txt CMakeLists.txt.v1.backup
   ```

2. **Install v2.x**
   ```bash
   pip install --upgrade gmake2cmake>=2.0.0
   gmake2cmake --version
   ```

3. **Migrate Configuration**
   ```bash
   # Use migration script
   python migrate_config.py

   # Or manually update configuration
   vim gmake2cmake.yaml
   ```

4. **Validate Configuration**
   ```bash
   gmake2cmake --config gmake2cmake.yaml --validate-config
   ```

5. **Run Conversion**
   ```bash
   # Generate new CMake files
   gmake2cmake --config gmake2cmake.yaml

   # Compare with backup
   diff CMakeLists.txt CMakeLists.txt.v1.backup
   ```

6. **Test Build**
   ```bash
   mkdir build-v2
   cd build-v2
   cmake ..
   cmake --build .
   ```

7. **Update CI/CD Pipelines**
   ```yaml
   # .github/workflows/build.yml
   - name: Convert Makefile to CMake
     run: |
       pip install gmake2cmake>=2.0.0
       gmake2cmake --config gmake2cmake.yaml
   ```

---

## Migrating Projects from Make to CMake

### Phase 1: Initial Conversion

#### Step 1: Analyze Makefile Structure

```bash
# Count targets
grep "^[a-zA-Z].*:" Makefile | wc -l

# Identify subdirectories
grep "^\s*\$(MAKE)" Makefile | grep -o "\-C [^ ]*" | cut -d' ' -f2

# List variables
grep "^[A-Z_]*\s*[:?]?=" Makefile | cut -d= -f1
```

#### Step 2: Create Configuration

```yaml
# gmake2cmake.yaml - Initial conversion
project_name: "LegacyProject"
cmake_minimum_version: "3.15"

output:
  directory: "cmake"  # Keep separate initially
  overwrite: false

makefiles:
  - "Makefile"
  # Add subdirectories as needed

targets:
  exclude:
    - "clean"
    - "distclean"
    - "install"  # Handle separately

diagnostics:
  level: "info"
  format: "markdown"
  output: "conversion_report.md"
```

#### Step 3: Run Initial Conversion

```bash
# Create output directory
mkdir -p cmake

# Run conversion
gmake2cmake --config gmake2cmake.yaml

# Review diagnostic report
cat conversion_report.md
```

#### Step 4: Review Generated CMake

```bash
# Compare structure
tree cmake/
tree .

# Review main CMakeLists.txt
less cmake/CMakeLists.txt
```

### Phase 2: Incremental Migration

#### Parallel Build System Strategy

Maintain both Make and CMake during transition:

```
project/
├── Makefile                 # Legacy Make build
├── CMakeLists.txt          # New CMake build (copied from cmake/)
├── cmake/                   # Generated CMake files (working directory)
├── gmake2cmake.yaml        # Conversion configuration
└── build/
    ├── make/               # Make build output
    └── cmake/              # CMake build output
```

#### Validate Equivalence

```bash
# Build with Make
make clean
make -j4
ls -lh build/make/

# Build with CMake
rm -rf build/cmake
mkdir build/cmake
cd build/cmake
cmake ../..
cmake --build . -j4
ls -lh .

# Compare outputs
diff build/make/myapp build/cmake/myapp
```

#### Identify Gaps

Create checklist of differences:

```markdown
## Build Comparison Checklist

- [ ] All executables built successfully
- [ ] All libraries built successfully
- [ ] Executables have same functionality
- [ ] Libraries have same symbols
- [ ] File sizes similar (accounting for debug info)
- [ ] Performance equivalent
- [ ] Tests pass with both builds
```

### Phase 3: Manual Refinement

#### Common Refinements Needed

1. **Generated File Handling**

   **gmake2cmake Output:**
   ```cmake
   # May not fully handle generation
   add_executable(myapp
       main.c
       generated.c  # Warning: may not exist
   )
   ```

   **Refined:**
   ```cmake
   # Add custom command for generation
   find_program(CODEGEN codegen REQUIRED)

   add_custom_command(
       OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/generated.c
       COMMAND ${CODEGEN}
           ${CMAKE_CURRENT_SOURCE_DIR}/template.c.in
           ${CMAKE_CURRENT_BINARY_DIR}/generated.c
       DEPENDS codegen template.c.in
       COMMENT "Generating source files"
   )

   add_executable(myapp
       main.c
       ${CMAKE_CURRENT_BINARY_DIR}/generated.c
   )
   ```

2. **Install Rules**

   **Add manually:**
   ```cmake
   # Install executables
   install(TARGETS myapp
       RUNTIME DESTINATION bin
   )

   # Install libraries
   install(TARGETS mylib
       LIBRARY DESTINATION lib
       ARCHIVE DESTINATION lib
   )

   # Install headers
   install(DIRECTORY include/
       DESTINATION include
       FILES_MATCHING PATTERN "*.h"
   )

   # Install documentation
   install(FILES README.md LICENSE
       DESTINATION share/doc/myapp
   )
   ```

3. **Testing Integration**

   **Add CTest:**
   ```cmake
   # Enable testing
   enable_testing()

   # Add tests
   add_test(NAME unit_tests
       COMMAND myapp --test
   )

   add_test(NAME integration_tests
       COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/tests/run_tests.sh
   )

   # Set test properties
   set_tests_properties(unit_tests PROPERTIES
       TIMEOUT 60
       ENVIRONMENT "TEST_DATA=${CMAKE_CURRENT_SOURCE_DIR}/tests/data"
   )
   ```

4. **Package Configuration**

   **Add CMake package config:**
   ```cmake
   # Generate package config files
   include(CMakePackageConfigHelpers)

   write_basic_package_version_file(
       "${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfigVersion.cmake"
       VERSION ${PROJECT_VERSION}
       COMPATIBILITY AnyNewerVersion
   )

   configure_package_config_file(
       "${CMAKE_CURRENT_SOURCE_DIR}/Config.cmake.in"
       "${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfig.cmake"
       INSTALL_DESTINATION lib/cmake/MyProject
   )

   install(FILES
       "${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfig.cmake"
       "${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfigVersion.cmake"
       DESTINATION lib/cmake/MyProject
   )
   ```

### Phase 4: Team Transition

#### Documentation for Developers

Create `docs/cmake_migration.md`:

```markdown
# CMake Migration Guide for Developers

## Quick Reference

| Make Command | CMake Equivalent |
|--------------|-----------------|
| `make` | `cmake --build build` |
| `make clean` | `cmake --build build --target clean` |
| `make install` | `cmake --install build` |
| `make test` | `ctest --test-dir build` |

## Building with CMake

### Initial Setup
```bash
mkdir build
cd build
cmake ..
```

### Regular Build
```bash
cmake --build build -j4
```

### Debug Build
```bash
mkdir build-debug
cd build-debug
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build .
```

### Installation
```bash
cmake --install build --prefix /opt/myapp
```

## Common Tasks

[Add project-specific instructions]
```

#### CI/CD Updates

**Before (Make):**
```yaml
# .github/workflows/build.yml
jobs:
  build:
    steps:
      - name: Build
        run: make -j4
      - name: Test
        run: make test
      - name: Install
        run: make install PREFIX=/opt/myapp
```

**After (CMake):**
```yaml
# .github/workflows/build.yml
jobs:
  build:
    steps:
      - name: Configure
        run: cmake -B build -DCMAKE_BUILD_TYPE=Release
      - name: Build
        run: cmake --build build -j4
      - name: Test
        run: ctest --test-dir build --output-on-failure
      - name: Install
        run: cmake --install build --prefix /opt/myapp
```

#### Gradual Rollout

1. **Week 1-2: Parallel Systems**
   - Both Make and CMake available
   - Developers can use either
   - CI runs both, compares results

2. **Week 3-4: CMake Primary**
   - CMake is default
   - Make still available as fallback
   - Documentation updated to CMake

3. **Week 5-6: CMake Only**
   - Remove Makefiles
   - Update all documentation
   - Archive Make build artifacts

### Phase 5: Cleanup

#### Remove Legacy Files

```bash
# Archive old Makefiles
mkdir archive/
mv Makefile archive/
find . -name "Makefile" -exec mv {} archive/ \;

# Remove Make-specific files
rm -rf build/make/
rm -f .make_cache

# Update .gitignore
cat >> .gitignore << EOF
# CMake
build/
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
*.cmake
!CMakeLists.txt
EOF
```

#### Update Documentation

```bash
# Update README
sed -i 's/make/cmake --build build/g' README.md
sed -i 's/Makefile/CMakeLists.txt/g' README.md

# Update INSTALL
cat > INSTALL << EOF
# Installation

## Build Requirements
- CMake 3.15 or higher
- C/C++ compiler
- [Other dependencies]

## Building
\`\`\`bash
mkdir build
cd build
cmake ..
cmake --build .
\`\`\`

## Installing
\`\`\`bash
cmake --install build --prefix /usr/local
\`\`\`
EOF
```

---

## Rollback Plan

If migration encounters serious issues:

### Step 1: Stop Using CMake

```bash
# Stop CI/CD CMake builds
git revert <cmake-commit>

# Notify team
echo "Reverting to Make build system temporarily"
```

### Step 2: Restore Make Build

```bash
# Restore from archive
cp archive/Makefile .
find archive/ -name "Makefile" -exec cp {} . \;

# Verify Make build works
make clean
make -j4
make test
```

### Step 3: Diagnose Issues

```bash
# Review conversion report
cat conversion_report.md

# Enable debug logging
GMAKE2CMAKE_LOG_LEVEL=DEBUG gmake2cmake -vvv --config gmake2cmake.yaml

# Compare Make and CMake outputs
diff -r build/make build/cmake
```

### Step 4: Fix and Retry

```bash
# Address issues in configuration or Makefiles
vim gmake2cmake.yaml

# Re-run conversion
gmake2cmake --config gmake2cmake.yaml

# Test incrementally
cmake -B build-test
cmake --build build-test
```

---

## Getting Help with Migration

### Community Resources

- **Documentation**: https://gmake2cmake.readthedocs.io/migration
- **Examples**: https://github.com/your-org/gmake2cmake/tree/main/examples
- **Discussions**: https://github.com/your-org/gmake2cmake/discussions

### Professional Services

For large or complex migrations, consider:
- Migration consulting
- Custom conversion rule development
- Training for development teams
- Post-migration support

Contact: support@gmake2cmake.example.com

## See Also

- [Configuration Guide](configuration.md) - Detailed configuration
- [Use Cases](use_cases.md) - Example scenarios
- [Troubleshooting](troubleshooting.md) - Common issues
