# Common Use Cases

This guide demonstrates common scenarios for using gmake2cmake to convert Makefile-based projects to CMake.

## Use Case 1: Basic Single Makefile Conversion

### Scenario

You have a simple C project with a single Makefile that builds one executable.

### Project Structure

```
myproject/
├── Makefile
├── main.c
├── helper.c
└── helper.h
```

### Original Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2
TARGET = myapp

SOURCES = main.c helper.c
OBJECTS = $(SOURCES:.c=.o)

$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) -o $(TARGET)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
```

### Configuration

Create `gmake2cmake.yaml`:

```yaml
project_name: "MyApp"
cmake_minimum_version: "3.10"

output:
  directory: "."
  overwrite: false

makefiles:
  - "Makefile"

targets:
  exclude:
    - "clean"
```

### Running Conversion

```bash
cd myproject
gmake2cmake --config gmake2cmake.yaml
```

### Generated CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.10)
project(MyApp)

set(CMAKE_C_FLAGS "-Wall -O2")

add_executable(myapp
    main.c
    helper.c
)
```

### Building with CMake

```bash
mkdir build
cd build
cmake ..
cmake --build .
```

### Key Takeaways

- Simple Makefiles convert directly to CMake
- Pattern rules (`%.o: %.c`) are handled automatically
- Phony targets like `clean` should be excluded
- Source file dependencies are preserved

---

## Use Case 2: Multi-Target Library and Executable Project

### Scenario

You have a project that builds both a library and multiple executables that link against it.

### Project Structure

```
complex-project/
├── Makefile
├── lib/
│   ├── Makefile
│   ├── mylib.c
│   └── mylib.h
├── app1/
│   ├── Makefile
│   └── main1.c
└── app2/
    ├── Makefile
    └── main2.c
```

### Root Makefile

```makefile
SUBDIRS = lib app1 app2

all:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir; \
	done

clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir clean; \
	done
```

### lib/Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2 -fPIC
AR = ar

TARGET = libmylib.a
SOURCES = mylib.c
OBJECTS = $(SOURCES:.c=.o)

$(TARGET): $(OBJECTS)
	$(AR) rcs $(TARGET) $(OBJECTS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
```

### app1/Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2 -I../lib
LDFLAGS = -L../lib -lmylib

TARGET = app1
SOURCES = main1.c
OBJECTS = $(SOURCES:.c=.o)

$(TARGET): $(OBJECTS) ../lib/libmylib.a
	$(CC) $(OBJECTS) $(LDFLAGS) -o $(TARGET)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
```

### Configuration

```yaml
project_name: "ComplexProject"
cmake_minimum_version: "3.15"

output:
  directory: "."
  overwrite: false

makefiles:
  - "Makefile"
  - "lib/Makefile"
  - "app1/Makefile"
  - "app2/Makefile"

targets:
  exclude:
    - "clean"
    - "all"
  library_type: "STATIC"

variable_mappings:
  CFLAGS: "CMAKE_C_FLAGS"
```

### Running Conversion

```bash
gmake2cmake --config gmake2cmake.yaml
```

### Generated Root CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.15)
project(ComplexProject)

set(CMAKE_C_FLAGS "-Wall -O2")

add_subdirectory(lib)
add_subdirectory(app1)
add_subdirectory(app2)
```

### Generated lib/CMakeLists.txt

```cmake
add_library(mylib STATIC
    mylib.c
)

target_include_directories(mylib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)
```

### Generated app1/CMakeLists.txt

```cmake
add_executable(app1
    main1.c
)

target_include_directories(app1 PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../lib
)

target_link_libraries(app1 PRIVATE
    mylib
)
```

### Building with CMake

```bash
mkdir build
cd build
cmake ..
cmake --build .
```

### Key Takeaways

- Multi-directory projects are converted to `add_subdirectory()` structure
- Library dependencies are automatically detected and converted to `target_link_libraries()`
- Include paths are converted to `target_include_directories()`
- Subdirectory build order is preserved based on dependencies

---

## Use Case 3: Cross-Platform Build with Conditional Compilation

### Scenario

You have a project that builds on multiple platforms with platform-specific code.

### Project Structure

```
cross-platform/
├── Makefile
├── src/
│   ├── main.c
│   ├── common.c
│   ├── linux.c
│   └── windows.c
└── include/
    └── platform.h
```

### Original Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2 -Iinclude

TARGET = myapp

COMMON_SOURCES = src/main.c src/common.c

ifeq ($(OS),Windows_NT)
    PLATFORM_SOURCES = src/windows.c
    LDFLAGS = -lws2_32
else
    PLATFORM_SOURCES = src/linux.c
    LDFLAGS = -lpthread
endif

SOURCES = $(COMMON_SOURCES) $(PLATFORM_SOURCES)
OBJECTS = $(SOURCES:.c=.o)

$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) $(LDFLAGS) -o $(TARGET)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
```

### Configuration

```yaml
project_name: "CrossPlatformApp"
cmake_minimum_version: "3.15"

output:
  directory: "."
  overwrite: false

makefiles:
  - "Makefile"

targets:
  exclude:
    - "clean"
```

### Running Conversion

```bash
gmake2cmake --config gmake2cmake.yaml
```

### Generated CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.15)
project(CrossPlatformApp)

set(CMAKE_C_FLAGS "-Wall -O2")

set(COMMON_SOURCES
    src/main.c
    src/common.c
)

if(WIN32)
    set(PLATFORM_SOURCES src/windows.c)
    set(PLATFORM_LIBS ws2_32)
else()
    set(PLATFORM_SOURCES src/linux.c)
    set(PLATFORM_LIBS pthread)
endif()

add_executable(myapp
    ${COMMON_SOURCES}
    ${PLATFORM_SOURCES}
)

target_include_directories(myapp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(myapp PRIVATE
    ${PLATFORM_LIBS}
)
```

### Manual Enhancement

You can further enhance the generated CMakeLists.txt:

```cmake
cmake_minimum_required(VERSION 3.15)
project(CrossPlatformApp C)

# Common sources
set(COMMON_SOURCES
    src/main.c
    src/common.c
)

# Platform-specific sources
if(WIN32)
    set(PLATFORM_SOURCES src/windows.c)
    set(PLATFORM_LIBS ws2_32)
elseif(UNIX AND NOT APPLE)
    set(PLATFORM_SOURCES src/linux.c)
    set(PLATFORM_LIBS pthread)
elseif(APPLE)
    set(PLATFORM_SOURCES src/macos.c)
    set(PLATFORM_LIBS pthread)
endif()

add_executable(myapp
    ${COMMON_SOURCES}
    ${PLATFORM_SOURCES}
)

target_include_directories(myapp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(myapp PRIVATE
    ${PLATFORM_LIBS}
)

# Compiler-specific flags
if(MSVC)
    target_compile_options(myapp PRIVATE /W4)
else()
    target_compile_options(myapp PRIVATE -Wall -Wextra)
endif()
```

### Key Takeaways

- Conditional compilation is converted to CMake `if()` statements
- Platform detection (`OS=Windows_NT`) maps to CMake variables (`WIN32`)
- Platform-specific libraries are detected and preserved
- Generated CMake can be enhanced with more sophisticated platform detection

---

## Use Case 4: Large Legacy Project with Generated Files

### Scenario

You have a large legacy project with build-time code generation, multiple libraries, and complex dependencies.

### Project Structure

```
legacy-project/
├── Makefile
├── config/
│   └── config.mk
├── tools/
│   ├── Makefile
│   └── codegen.c
├── lib/
│   ├── core/
│   │   └── Makefile
│   └── utils/
│       └── Makefile
└── apps/
    ├── server/
    │   └── Makefile
    └── client/
        └── Makefile
```

### Root Makefile

```makefile
include config/config.mk

export CC
export CFLAGS

SUBDIRS = tools lib apps

all: tools
	for dir in lib apps; do \
		$(MAKE) -C $$dir; \
	done

tools:
	$(MAKE) -C tools

clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir clean; \
	done
```

### config/config.mk

```makefile
CC = gcc
CXX = g++
CFLAGS = -Wall -O2 -g
CXXFLAGS = -Wall -O2 -g -std=c++14
PREFIX = /usr/local
INSTALL = install
```

### tools/Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2

codegen: codegen.c
	$(CC) $(CFLAGS) codegen.c -o codegen

clean:
	rm -f codegen
```

### lib/core/Makefile

```makefile
CC = gcc
CFLAGS = -Wall -O2 -fPIC -Iinclude
AR = ar

# Generate source files
generated.c: ../../tools/codegen core.def
	../../tools/codegen core.def > generated.c

SOURCES = core.c utils.c generated.c
OBJECTS = $(SOURCES:.c=.o)

libcore.a: $(OBJECTS)
	$(AR) rcs libcore.a $(OBJECTS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) libcore.a generated.c
```

### Configuration

```yaml
project_name: "LegacyProject"
cmake_minimum_version: "3.18"
languages:
  - C
  - CXX

output:
  directory: "."
  overwrite: false

makefiles:
  - "Makefile"
  - "tools/Makefile"
  - "lib/core/Makefile"
  - "lib/utils/Makefile"
  - "apps/server/Makefile"
  - "apps/client/Makefile"

include_directories:
  - "config"

targets:
  exclude:
    - "clean"
    - "install"
    - "distclean"
  library_type: "STATIC"

diagnostics:
  level: "warning"
  format: "markdown"
  output: "conversion_report.md"

performance:
  parallel: true
  max_workers: 4
  cache: true
```

### Running Conversion

```bash
gmake2cmake --config gmake2cmake.yaml --log-level info
```

### Generated Root CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.18)
project(LegacyProject C CXX)

set(CMAKE_C_FLAGS "-Wall -O2 -g")
set(CMAKE_CXX_FLAGS "-Wall -O2 -g -std=c++14")
set(CMAKE_INSTALL_PREFIX "/usr/local")

add_subdirectory(tools)
add_subdirectory(lib/core)
add_subdirectory(lib/utils)
add_subdirectory(apps/server)
add_subdirectory(apps/client)
```

### Generated tools/CMakeLists.txt

```cmake
add_executable(codegen
    codegen.c
)

# Export codegen for use in other directories
export(TARGETS codegen FILE ${CMAKE_BINARY_DIR}/CodegenTargets.cmake)
```

### Generated lib/core/CMakeLists.txt

```cmake
# Import codegen tool
include(${CMAKE_BINARY_DIR}/CodegenTargets.cmake)

# Generate source files
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/generated.c
    COMMAND codegen ${CMAKE_CURRENT_SOURCE_DIR}/core.def > ${CMAKE_CURRENT_BINARY_DIR}/generated.c
    DEPENDS codegen core.def
    COMMENT "Generating source files with codegen"
)

add_library(core STATIC
    core.c
    utils.c
    ${CMAKE_CURRENT_BINARY_DIR}/generated.c
)

target_include_directories(core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

### Post-Conversion Manual Steps

1. **Review Generated Files Handling**: Verify custom commands are correct
2. **Add Install Targets**:
   ```cmake
   install(TARGETS core utils server client
       ARCHIVE DESTINATION lib
       RUNTIME DESTINATION bin
   )
   ```
3. **Add Testing**: Convert test Makefiles or add CTest configuration
4. **Documentation**: Add project-specific CMake documentation

### Building with CMake

```bash
mkdir build
cd build
cmake ..
cmake --build . -j 4
cmake --install . --prefix /opt/legacy-project
```

### Key Takeaways

- Large projects benefit from parallel processing configuration
- Generated files are converted to `add_custom_command()`
- Build order is preserved through dependency analysis
- Configuration includes can be processed
- Review conversion report for any unhandled constructs
- Manual post-processing may be needed for complex generation rules

---

## Performance Optimization Tips

### For Large Projects

1. **Enable Parallel Processing**:
   ```yaml
   performance:
     parallel: true
     max_workers: 8  # Adjust based on CPU cores
   ```

2. **Use Caching**:
   ```yaml
   performance:
     cache: true
     cache_directory: ".gmake2cmake_cache"
   ```

3. **Process Incrementally**: Convert subdirectories separately first, then integrate

4. **Suppress Unnecessary Diagnostics**:
   ```yaml
   diagnostics:
     suppress:
       - "UNKNOWN_FUNCTION"
       - "SHELL_COMMAND"
   ```

### For Complex Makefiles

1. **Pre-process Variables**: Define common variables in configuration
2. **Exclude Unnecessary Targets**: Focus on build targets, exclude utility targets
3. **Split Large Makefiles**: Break into smaller, more manageable files
4. **Use Diagnostic Reports**: Generate markdown reports for review

## See Also

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Troubleshooting Guide](troubleshooting.md) - Common problems and solutions
- [Performance Guide](performance.md) - Optimization techniques
