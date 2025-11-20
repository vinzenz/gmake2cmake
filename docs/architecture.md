# Architecture Overview

This document provides a comprehensive overview of the gmake2cmake architecture, including system design, data flow, key components, and extension points.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      gmake2cmake System                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   CLI/API    │─────>│  Controller  │─────>│  Config  │  │
│  └──────────────┘      └──────────────┘      └──────────┘  │
│         │                      │                     │       │
│         │                      v                     │       │
│         │              ┌──────────────┐             │       │
│         │              │   Discovery  │<────────────┘       │
│         │              └──────────────┘                     │
│         │                      │                            │
│         │                      v                            │
│         │         ┌────────────────────────┐               │
│         │         │   Makefile Parser      │               │
│         │         │  (Lexer + Parser)      │               │
│         │         └────────────────────────┘               │
│         │                      │                            │
│         │                      v                            │
│         │         ┌────────────────────────┐               │
│         │         │  Variable Evaluator    │               │
│         │         │  (Expansion + Eval)    │               │
│         │         └────────────────────────┘               │
│         │                      │                            │
│         │                      v                            │
│         │         ┌────────────────────────┐               │
│         │         │    IR Builder          │               │
│         │         │  (AST -> IR)           │               │
│         │         └────────────────────────┘               │
│         │                      │                            │
│         │                      v                            │
│         │         ┌────────────────────────┐               │
│         │         │  IR Optimizer          │               │
│         │         │  (Patterns + Cycles)   │               │
│         │         └────────────────────────┘               │
│         │                      │                            │
│         │                      v                            │
│         │         ┌────────────────────────┐               │
│         │         │   CMake Emitter        │               │
│         │         │  (IR -> CMake)         │               │
│         │         └────────────────────────┘               │
│         │                      │                            │
│         v                      v                            │
│  ┌──────────────────────────────────────────┐             │
│  │         Diagnostic System                 │             │
│  │  (Error reporting + Logging)              │             │
│  └──────────────────────────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘

External I/O:
├─ Input: Makefiles (*.mk, Makefile, GNUmakefile)
├─ Input: Configuration (YAML/JSON)
├─ Output: CMakeLists.txt files
└─ Output: Diagnostic reports (Text/JSON/Markdown)
```

### Component Interactions

```
User Command
    │
    ├──> CLI Parser (cli.py)
    │        │
    │        ├──> Config Loader (config.py)
    │        │        │
    │        │        └──> Schema Validator (schema_validator.py)
    │        │
    │        └──> Converter Controller
    │                 │
    │                 ├──> Discovery (make/discovery.py)
    │                 │        │
    │                 │        └──> File System (fs.py)
    │                 │
    │                 ├──> Parser (make/parser.py)
    │                 │        │
    │                 │        └──> Lexer (make/lexer.py)
    │                 │
    │                 ├──> Evaluator (make/evaluator.py)
    │                 │        │
    │                 │        ├──> Variable Expansion
    │                 │        └──> Rule Evaluation
    │                 │
    │                 ├──> IR Builder (ir/builder.py)
    │                 │        │
    │                 │        ├──> Pattern Matcher (ir/patterns.py)
    │                 │        ├──> Cycle Detector (ir/cycles.py)
    │                 │        └──> Unknown Handler (ir/unknowns.py)
    │                 │
    │                 └──> Emitter (cmake/emitter.py)
    │                          │
    │                          └──> Template Renderer
    │
    └──> Diagnostic Collector (diagnostics.py)
             │
             ├──> Console Reporter
             ├──> File Reporter
             └──> Markdown Reporter (markdown_reporter.py)
```

## Core Components

### 1. Configuration System

**Location:** `gmake2cmake/config.py`

**Purpose:** Load, validate, and manage configuration settings.

**Key Classes:**
```python
class ConfigModel:
    """Main configuration data model.

    Attributes:
        project_name: Name of the CMake project
        cmake_minimum_version: Minimum CMake version
        output: Output configuration
        makefiles: List of Makefile paths
        variables: Predefined Make variables
        targets: Target configuration
        diagnostics: Diagnostic settings
        performance: Performance optimization settings
    """
```

**Data Flow:**
```
YAML/JSON File
    ↓
Schema Validation (config_schema.json)
    ↓
ConfigModel Instance
    ↓
Available to all components
```

**Example:**
```python
from gmake2cmake.config import load_config

config = load_config("gmake2cmake.yaml")
print(config.project_name)  # Access configuration
```

### 2. Makefile Discovery

**Location:** `gmake2cmake/make/discovery.py`

**Purpose:** Find and enumerate Makefile dependencies.

**Algorithm:**
```
1. Start with user-specified Makefiles
2. Parse each Makefile
3. Extract `include` directives
4. Recursively discover included files
5. Build dependency graph
6. Return topologically sorted list
```

**Key Functions:**
```python
def discover_makefiles(
    start_files: List[Path],
    include_dirs: List[Path]
) -> DiscoveryResult:
    """Discover all Makefiles and their dependencies.

    Args:
        start_files: Initial Makefile paths
        include_dirs: Additional include directories

    Returns:
        DiscoveryResult with ordered Makefiles and graph
    """
```

**Handles:**
- Relative includes: `include config.mk`
- Absolute includes: `include /usr/share/make/rules.mk`
- Optional includes: `-include optional.mk`
- Wildcard includes: `include *.mk`

### 3. Makefile Parser

**Location:** `gmake2cmake/make/parser.py`

**Purpose:** Parse Makefile syntax into Abstract Syntax Tree (AST).

**Architecture:**
```
Makefile Text
    ↓
Lexer (Tokenization)
    ↓
Token Stream
    ↓
Parser (Syntax Analysis)
    ↓
AST (Abstract Syntax Tree)
```

**AST Node Types:**
```python
@dataclass
class Assignment:
    """Variable assignment: VAR = value"""
    name: str
    operator: str  # '=', ':=', '?=', '+='
    value: str

@dataclass
class Rule:
    """Build rule: target: deps"""
    targets: List[str]
    dependencies: List[str]
    recipe: List[str]
    is_phony: bool

@dataclass
class Conditional:
    """Conditional directive: ifdef/ifndef/ifeq/ifneq"""
    condition: str
    true_branch: List[Node]
    false_branch: List[Node]

@dataclass
class Include:
    """Include directive: include file.mk"""
    path: str
    optional: bool
```

**Parser Features:**
- Recursive descent parsing
- Error recovery
- Line continuation handling
- Comment preservation
- Macro expansion tracking

### 4. Variable Evaluator

**Location:** `gmake2cmake/make/evaluator.py`

**Purpose:** Evaluate Make variables and expand references.

**Evaluation Context:**
```python
class EvaluationContext:
    """Context for variable evaluation.

    Maintains:
    - Variable definitions (by type)
    - Expansion stack (for recursion detection)
    - Target-specific variables
    - Automatic variables ($@, $<, etc.)
    """
```

**Variable Expansion:**
```
$(VAR)          → Simple expansion
$(VAR:%.o=%.c)  → Substitution reference
$(func arg)     → Function call
$$VAR           → Escaped $
$@              → Automatic variable
```

**Supported Functions:**
```
Text Functions:
- $(subst from,to,text)
- $(patsubst pattern,replacement,text)
- $(strip text)
- $(findstring find,text)
- $(filter pattern,text)
- $(filter-out pattern,text)

File Functions:
- $(wildcard pattern)
- $(dir names)
- $(notdir names)
- $(suffix names)
- $(basename names)
- $(addsuffix suffix,names)
- $(addprefix prefix,names)

Control Functions:
- $(if condition,then,else)
- $(or condition1,condition2,...)
- $(and condition1,condition2,...)
```

**Evaluation Algorithm:**
```python
def expand_variable(name: str, context: Context) -> str:
    """Expand variable reference.

    1. Check for recursion ($(VAR) references $(VAR))
    2. Look up variable in context
    3. Expand any nested references
    4. Apply substitutions if present
    5. Return expanded value
    """
```

### 5. IR Builder

**Location:** `gmake2cmake/ir/builder.py`

**Purpose:** Convert AST to Intermediate Representation (IR).

**IR Structure:**
```python
class Project:
    """Top-level project representation.

    Attributes:
        name: Project name
        targets: Dictionary of Target objects
        global_variables: Project-wide variables
        subdirectories: List of subdirectory Projects
    """

class Target:
    """Build target (executable, library, or custom).

    Attributes:
        name: Target name
        type: TargetType (EXECUTABLE, LIBRARY, CUSTOM)
        sources: Source files
        dependencies: Other targets this depends on
        properties: CMake properties (include dirs, compile flags, etc.)
    """
```

**Build Process:**
```
AST Rules
    ↓
Classify Targets
    ├─> Executable (links to executable)
    ├─> Static Library (uses ar/ranlib)
    ├─> Shared Library (has -shared flag)
    └─> Custom (other rules)
    ↓
Infer Source Files
    ├─> Pattern rules (%.o: %.c)
    ├─> Explicit rules (main.o: main.c)
    └─> Wildcard expansion
    ↓
Extract Dependencies
    ├─> Target prerequisites
    ├─> Library links (-l flags)
    └─> File dependencies
    ↓
Determine Properties
    ├─> Include directories (-I flags)
    ├─> Compile definitions (-D flags)
    ├─> Compiler flags (CFLAGS, etc.)
    └─> Linker flags (LDFLAGS, etc.)
    ↓
IR Target
```

**Target Classification:**
```python
def classify_target(rule: Rule, context: Context) -> TargetType:
    """Determine target type from rule.

    Heuristics:
    1. Check file extension (.a → STATIC, .so → SHARED)
    2. Check recipe commands (ar → STATIC, gcc -shared → SHARED)
    3. Check linking (-o → EXECUTABLE)
    4. Default to CUSTOM for unknown
    """
```

### 6. IR Optimizer

**Location:** `gmake2cmake/ir/patterns.py`, `gmake2cmake/ir/cycles.py`

**Purpose:** Optimize IR before emission.

**Optimizations:**

1. **Pattern Recognition**
   ```python
   # Recognize common patterns
   - Compile pattern: %.o: %.c
   - Archive pattern: lib%.a: %.o
   - Link pattern: %: %.o
   ```

2. **Dependency Cycles**
   ```python
   # Detect and break circular dependencies
   def detect_cycles(targets: Dict[str, Target]) -> List[Cycle]:
       """Use Tarjan's algorithm to find strongly connected components."""
   ```

3. **Dead Code Elimination**
   ```python
   # Remove unused targets
   def eliminate_unused(project: Project, roots: List[str]) -> Project:
       """Keep only targets reachable from roots."""
   ```

4. **Variable Propagation**
   ```python
   # Propagate target-specific variables to properties
   def propagate_variables(target: Target) -> Target:
       """Convert Make variables to CMake properties."""
   ```

### 7. CMake Emitter

**Location:** `gmake2cmake/cmake/emitter.py`

**Purpose:** Generate CMakeLists.txt from IR.

**Emission Strategy:**
```
IR Project
    ↓
Render Header
    ├─> cmake_minimum_required()
    ├─> project()
    └─> Global variables
    ↓
Render Targets
    ├─> add_executable() / add_library()
    ├─> target_sources()
    ├─> target_include_directories()
    ├─> target_compile_definitions()
    ├─> target_compile_options()
    └─> target_link_libraries()
    ↓
Render Subdirectories
    └─> add_subdirectory()
    ↓
Write CMakeLists.txt
```

**Template System:**
```python
# Templates for CMake constructs
TEMPLATES = {
    'project': """cmake_minimum_required(VERSION {version})
project({name} {languages})
""",
    'executable': """add_executable({name}
    {sources}
)
""",
    'library': """add_library({name} {type}
    {sources}
)
""",
}

def emit_target(target: Target) -> str:
    """Render target to CMake syntax."""
    template = TEMPLATES[target.type]
    return template.format(**target.properties)
```

**Formatting Options:**
```python
class EmitOptions:
    """Control CMake output formatting.

    Attributes:
        indent: Indentation string (default: "    ")
        line_width: Maximum line width (default: 80)
        sort_sources: Sort source files alphabetically
        group_properties: Group related properties
        add_comments: Add explanatory comments
    """
```

### 8. Diagnostic System

**Location:** `gmake2cmake/diagnostics.py`

**Purpose:** Collect, report, and manage diagnostic messages.

**Diagnostic Levels:**
```python
class DiagnosticLevel(Enum):
    ERROR = 4    # Prevents successful conversion
    WARNING = 3  # Potential issues
    INFO = 2     # Informational messages
    HINT = 1     # Suggestions for improvement
```

**Diagnostic Collection:**
```python
class DiagnosticCollector:
    """Collect diagnostics during conversion.

    Methods:
        error(code, message, location): Add error
        warning(code, message, location): Add warning
        info(code, message, location): Add info
        hint(code, message, location): Add hint
    """

# Usage in components
def parse_rule(line: str, collector: DiagnosticCollector):
    if not is_valid_target(line):
        collector.warning(
            "INVALID_TARGET",
            f"Target name '{line}' may not be valid",
            location=current_location
        )
```

**Reporting Formats:**
```python
class TextReporter:
    """Console-friendly text output."""

class JSONReporter:
    """Machine-readable JSON output."""

class MarkdownReporter:
    """Human-readable report with statistics."""
```

## Data Flow

### Complete Conversion Pipeline

```
1. Initialization
   User → CLI → Config Loader → Config Model

2. Discovery
   Config → Discovery → Makefile List

3. Parsing (Per Makefile)
   Makefile → Lexer → Tokens
   Tokens → Parser → AST

4. Evaluation
   AST + Context → Evaluator → Expanded AST

5. IR Building
   Expanded AST → IR Builder → IR Project

6. Optimization
   IR Project → Optimizer → Optimized IR

7. Emission
   Optimized IR → Emitter → CMakeLists.txt

8. Diagnostics (Throughout)
   Each Stage → Collector → Reporter → Output
```

### State Management

**Global State:**
```python
class ConversionState:
    """Maintains state across conversion.

    Attributes:
        config: Configuration settings
        discovered_files: All Makefiles found
        parsed_asts: Cache of parsed ASTs
        ir_projects: Generated IR
        diagnostics: Collected diagnostics
    """
```

**Thread Safety:**
- Parallel processing uses separate state per thread
- Shared state protected with locks
- Results merged after completion

## Extension Points

### 1. Custom Target Types

```python
# ir/builder.py
class CustomTargetClassifier:
    """Extend target classification.

    Register custom classifiers:
    """
    def classify(self, rule: Rule) -> Optional[TargetType]:
        if self.is_custom_type(rule):
            return CustomTargetType.MY_TYPE
        return None

# Usage
builder.register_classifier(CustomTargetClassifier())
```

### 2. Custom CMake Generators

```python
# cmake/emitter.py
class CustomEmitter(Emitter):
    """Custom CMake generation logic."""

    def emit_custom_target(self, target: Target) -> str:
        # Custom CMake generation
        return f"add_custom_target({target.name} ...)"

# Usage
emitter = CustomEmitter(config)
```

### 3. Custom Diagnostic Rules

```python
# diagnostics.py
class CustomDiagnosticRule:
    """Add custom validation rules."""

    def check(self, ir: Project, collector: DiagnosticCollector):
        for target in ir.targets.values():
            if self.violates_policy(target):
                collector.warning(
                    "CUSTOM_POLICY",
                    f"Target {target.name} violates policy",
                    location=target.location
                )

# Usage
validator.register_rule(CustomDiagnosticRule())
```

### 4. Custom Variable Functions

```python
# make/evaluator.py
def custom_function(args: List[str], context: Context) -> str:
    """Custom Make function.

    Usage in Makefile:
        RESULT = $(custom-function arg1 arg2)
    """
    # Implementation
    return result

# Register
evaluator.register_function("custom-function", custom_function)
```

## Performance Considerations

### Parallel Processing

**Strategy:**
```python
# parallel.py
class ParallelProcessor:
    """Process Makefiles in parallel.

    - Independent Makefiles processed concurrently
    - Dependency order respected
    - Results merged in topological order
    """
```

**Parallelization Points:**
1. Discovery (independent file searches)
2. Parsing (independent Makefile parsing)
3. IR building (per-directory projects)

### Caching

**Cache Strategy:**
```python
# cache.py
class ConversionCache:
    """Cache parsed and processed results.

    Cache Keys:
    - File path + modification time
    - Configuration hash

    Cached Data:
    - Parsed AST
    - Expanded variables
    - IR representations
    """
```

**Cache Invalidation:**
- File modification time changes
- Configuration changes
- Include file changes

### Memory Management

**Large Project Handling:**
```python
# Process in chunks
def process_large_project(files: List[Path]):
    for chunk in chunks(files, size=100):
        results = process_chunk(chunk)
        yield results  # Stream results
```

## See Also

- [Contributing Guide](../CONTRIBUTING.md) - Development guidelines
- [Testing Guide](testing.md) - Testing strategies
- [Performance Guide](performance.md) - Optimization techniques
- [API Reference](api/) - Detailed API documentation
