# Task Execution Plan

## Executive Summary

This execution plan coordinates the implementation of 43 code quality tasks (TASK-0012 through TASK-0054) for the gmake2cmake project using parallel haiku-model agents. The strategy is organized into 5 execution phases with 13 parallel batches and 6 sequential batches, leveraging the Task tool for agent coordination.

**Key Metrics:**
- **Total Tasks**: 41 unique tasks (2 duplicates identified: TASK-0043, TASK-0054)
- **Parallel Execution**: 67% of tasks (27 tasks) can run concurrently
- **Sequential Execution**: 33% of tasks (14 tasks) require ordering
- **Critical Path**: 4 foundational infrastructure tasks unblock 32 downstream tasks
- **Quality Gates**: 14 validation checkpoints with full test suite runs
- **Estimated Duration**: 5-8 phases with checkpoint-driven progress

**Risk Mitigation:**
- High-risk tasks (FileSystemAdapter, error recovery, multiprocessing) isolated with dedicated testing
- Test suite validation after every batch
- Archive and commit after each task completion
- Rollback procedures defined for each phase

## Execution Phases

### Phase 1: Foundation Infrastructure
<phase_1>
**Objective**: Establish core infrastructure modules that unblock downstream work

**Parallel Batch 1A (New Infrastructure - 3 tasks, Independent)**
- TASK-0041: Centralize constants (creates constants.py) - Agent: haiku
- TASK-0025: Diagnostic code registry (creates diagnostics/codes.py) - Agent: haiku
- TASK-0031: Deterministic ordering utilities (creates utils/ordering.py) - Agent: haiku

**Validation 1A:**
- Run: `pytest -q tests/`
- Run: `ruff check .`
- Verify: All tests pass, no new linting errors, new modules importable

**Parallel Batch 1B (Code Quality - 5 tasks, Independent)**
- TASK-0034: Resolve __all__ declaration (__init__.py) - Agent: haiku
- TASK-0035: Add type hints in CLI helpers (cli.py) - Agent: haiku
- TASK-0039: Add docstrings to public dataclasses - Agent: haiku
- TASK-0040: Standardize import ordering - Agent: haiku
- TASK-0051: Define test coverage strategy - Agent: haiku

**Validation 1B:**
- Run: `ruff check . --select I,D,ANN`
- Run: `mypy gmake2cmake/`
- Verify: Import ordering consistent, docstrings improved, type hints present

**Sequential Batch 1C (Filesystem Foundation - 2 tasks, High Risk)**
- TASK-0019: FileSystemAdapter interface (creates filesystem.py, foundational) - Agent: haiku
  - **CRITICAL**: Affects ALL modules, requires careful integration
  - Wait for completion and validation before proceeding
- TASK-0042: FileSystem error handling (depends on TASK-0019) - Agent: haiku

**Validation 1C:**
- Run: `pytest -q tests/test_filesystem.py tests/test_discovery.py`
- Run: `pytest -q tests/test_integration*.py`
- Verify: FileSystemAdapter works, no direct filesystem access in core modules

**Parallel Batch 1D (Simple Refactors - 3 tasks, Depends on 1A+1C)**
- TASK-0037: Extract magic numbers in unknowns (depends on TASK-0041) - Agent: haiku
- TASK-0044: Path normalization validation - Agent: haiku
- TASK-0048: Type annotations for diagnostic structures - Agent: haiku

**Validation 1D:**
- Run: `pytest -q tests/test_unknowns.py tests/test_config_manager.py`
- Verify: Constants used correctly, path validation functional
</phase_1>

### Phase 2: Module-Specific Improvements
<phase_2>
**Objective**: Refactor individual modules with targeted improvements

**Parallel Batch 2A (Discovery and Parser - 5 tasks, Independent)**
- TASK-0012: CLI imports cleanup (depends on TASK-0041) - Agent: haiku
- TASK-0013: UnknownConstruct messaging (depends on TASK-0025, TASK-0037) - Agent: haiku
- TASK-0015: Fix -include handling in discovery (depends on TASK-0019) - Agent: haiku
- TASK-0030: Recursive Make traversal (depends on TASK-0019) - Agent: haiku
- TASK-0045: Refactor parser control flow (depends on TASK-0048) - Agent: haiku

**Validation 2A:**
- Run: `pytest -q tests/test_discovery.py tests/test_parser.py tests/test_cli.py`
- Run: `pytest -q tests/test_evaluator.py`
- Verify: -include works, recursive Make detected, parser maintains behavior

**Parallel Batch 2B (Config and Utilities - 3 tasks, Independent)**
- TASK-0033: Config schema validation (depends on TASK-0041) - Agent: haiku
  - **NOTE**: Skip TASK-0054 as duplicate
- TASK-0036: Standardize exception handling (depends on TASK-0041) - Agent: haiku
- TASK-0046: Logging strategy - Agent: haiku

**Validation 2B:**
- Run: `pytest -q tests/test_config_manager.py tests/test_cli.py`
- Run: `pytest -q tests/ --log-level=DEBUG`
- Verify: Config validation works, exceptions consistent, logging configured

**Sequential Batch 2C (Evaluator Enhancements - 4 tasks, Sequential within group)**
- TASK-0049: Context managers for resource handling (depends on TASK-0019, TASK-0042) - Agent: haiku
  - Wait for completion before next task
- TASK-0028: Recursive loop detection in evaluator (depends on TASK-0025) - Agent: haiku
  - Wait for completion before next task
- TASK-0020: Caching layer for evaluator (after TASK-0028) - Agent: haiku
  - Wait for completion before next task
- TASK-0029: Complex Make functions (depends on TASK-0025) - Agent: haiku

**Validation 2C:**
- Run: `pytest -q tests/test_evaluator.py tests/evaluator/`
- Verify: Loop detection works, caching provides speedup, complex functions supported
</phase_2>

### Phase 3: IR Builder Core
<phase_3>
**Objective**: Enhance IR builder foundation before adding features

**Sequential Batch 3A (IR Builder Base - 3 tasks, Sequential)**
- TASK-0038: Fix alias assignment logic (depends on TASK-0037) - Agent: haiku
  - Wait for completion before next task
- TASK-0047: Optimize set merges in build_targets - Agent: haiku
  - Wait for completion before next task
- TASK-0018: Global config normalization (depends on TASK-0041, TASK-0036) - Agent: haiku

**Validation 3A:**
- Run: `pytest -q tests/ir/test_ir_builder.py`
- Run: `pytest -q tests/emitter/test_emitter.py`
- Verify: Alias assignment correct, optimization working, config normalized

**Parallel Batch 3B (IR Builder Features - 4 tasks, After 3A)**
- TASK-0016: Custom commands preservation (depends on Layer 3A) - Agent: haiku
- TASK-0017: Target mapping link libs and visibility (depends on Layer 3A) - Agent: haiku
- TASK-0022: Pattern rule instantiation (depends on TASK-0019, TASK-0031) - Agent: haiku
- TASK-0023: Dependency cycle detection (depends on TASK-0031) - Agent: haiku

**Validation 3B:**
- Run: `pytest -q tests/ir/test_ir_builder.py`
- Run: `pytest -q tests/ir/test_pattern_instantiation.py`
- Run: `pytest -q tests/ir/test_dependency_cycles.py`
- Verify: Custom commands preserved, visibility honored, cycles detected
</phase_3>

### Phase 4: Emitter and Advanced Features
<phase_4>
**Objective**: Complete emitter updates and add advanced capabilities

**Sequential Batch 4A (Emitter Updates - 1 task)**
- TASK-0014: Detect unmappable constructs (depends on TASK-0037, TASK-0041) - Agent: haiku
  - **NOTE**: Must update emitter for TASK-0016, TASK-0017, TASK-0018 changes

**Validation 4A:**
- Run: `pytest -q tests/emitter/`
- Run: `pytest -q tests/ir/`
- Run: `pytest -q tests/test_integration*.py`
- Verify: Unmappable constructs detected, CMake output valid

**Parallel Batch 4B (Advanced Features - 3 tasks, Independent)**
- TASK-0021: Multiprocessing support (depends on TASK-0020 optionally) - Agent: haiku
  - **HIGH RISK**: Concurrency bugs, requires extra testing
- TASK-0032: Markdown report generator (depends on TASK-0025) - Agent: haiku
- TASK-0052: CLI exit code strategy (depends on TASK-0025) - Agent: haiku

**Validation 4B:**
- Run: `pytest -q tests/test_parallel_evaluation.py -n auto`
- Run: `pytest -q tests/diagnostics/test_markdown_report.py`
- Verify: Multiprocessing produces identical output, reports generated

**Sequential Batch 4C (Validation and Error Recovery - 2 tasks, High Risk)**
- TASK-0050: Dataclass validation (depends on Phase 3) - Agent: haiku
  - Wait for completion before next task
- TASK-0024: Error recovery and partial conversion (depends on most tasks) - Agent: haiku
  - **CRITICAL**: Requires most pipeline tasks complete

**Validation 4C:**
- Run: `pytest -q tests/test_error_recovery.py`
- Run: `pytest -q tests/ --maxfail=1`
- Verify: Validation catches invalid inputs, error recovery allows partial conversion
</phase_4>

### Phase 5: Testing and Documentation
<phase_5>
**Objective**: Comprehensive testing and user-facing improvements

**Parallel Batch 5A (Final Polish - 3 tasks, Independent)**
- TASK-0027: CLI help system (depends on TASK-0012, TASK-0025) - Agent: haiku
- TASK-0026: Integration test scenarios (depends on all pipeline tasks) - Agent: haiku
- TASK-0053: Performance profiling (depends on pipeline completion) - Agent: haiku

**Final Validation:**
- Run: `pytest -q tests/integration/test_scenarios.py -v --scenario=all`
- Run: `pytest -q tests/ --cov=gmake2cmake --cov-report=html`
- Run: `gmake2cmake --help`
- Verify: All 26 integration scenarios pass, coverage meets target (80%+), help comprehensive
</phase_5>

## Agent Coordination

### Parallel Execution Commands
<parallel_commands>
# Phase 1, Batch 1A - Foundation Infrastructure (3 agents)
agents_1a = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0041: Centralize constants

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0041.md
2. Create gmake2cmake/constants.py with centralized constants
3. Update all modules to import from constants.py
4. Run tests: pytest -q tests/
5. Archive task: mv tasks/TASK-0041.md tasks/archive/
6. Commit: "Complete TASK-0041: Centralize default values and constants"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0025: Diagnostic code registry

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0025.md
2. Create gmake2cmake/diagnostics/codes.py with diagnostic registry
3. Define enum or registry for all diagnostic codes
4. Run tests: pytest -q tests/
5. Archive task: mv tasks/TASK-0025.md tasks/archive/
6. Commit: "Complete TASK-0025: Create centralized diagnostic code registry"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0031: Deterministic ordering utilities

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0031.md
2. Create gmake2cmake/utils/ordering.py with ordering utilities
3. Implement deterministic sorting/ordering functions
4. Run tests: pytest -q tests/
5. Archive task: mv tasks/TASK-0031.md tasks/archive/
6. Commit: "Complete TASK-0031: Implement deterministic ordering utilities"
"""
    )
]

# Phase 1, Batch 1B - Code Quality (5 agents)
agents_1b = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0034: Resolve __all__ declaration

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0034.md
2. Update gmake2cmake/__init__.py with proper __all__ exports
3. Run tests: pytest -q tests/
4. Archive task: mv tasks/TASK-0034.md tasks/archive/
5. Commit: "Complete TASK-0034: Resolve empty __all__ declaration"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0035: Add type hints in CLI helpers

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0035.md
2. Add type annotations to gmake2cmake/cli.py helper functions
3. Run mypy: mypy gmake2cmake/cli.py
4. Run tests: pytest -q tests/test_cli.py
5. Archive task: mv tasks/TASK-0035.md tasks/archive/
6. Commit: "Complete TASK-0035: Add missing type hints in CLI helpers"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0039: Add docstrings to public dataclasses

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0039.md
2. Add docstrings to all public dataclasses across modules
3. Run ruff: ruff check . --select D
4. Run tests: pytest -q tests/
5. Archive task: mv tasks/TASK-0039.md tasks/archive/
6. Commit: "Complete TASK-0039: Add docstrings to public dataclasses"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0040: Standardize import ordering

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0040.md
2. Standardize imports across all modules (stdlib, third-party, local)
3. Run ruff: ruff check . --select I
4. Run tests: pytest -q tests/
5. Archive task: mv tasks/TASK-0040.md tasks/archive/
6. Commit: "Complete TASK-0040: Standardize import ordering and style"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0051: Define test coverage strategy

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0051.md
2. Update pyproject.toml with coverage configuration
3. Document coverage targets and exclusions
4. Run coverage: pytest --cov=gmake2cmake --cov-report=term
5. Archive task: mv tasks/TASK-0051.md tasks/archive/
6. Commit: "Complete TASK-0051: Define test coverage strategy"
"""
    )
]

# Phase 1, Batch 1D - Simple Refactors (3 agents)
agents_1d = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0037: Extract magic numbers in unknowns

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0037.md
2. Extract magic numbers to constants in gmake2cmake/ir/unknowns.py
3. Import constants from constants.py (created in TASK-0041)
4. Run tests: pytest -q tests/test_unknowns.py
5. Archive task: mv tasks/TASK-0037.md tasks/archive/
6. Commit: "Complete TASK-0037: Extract magic numbers to named constants"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0044: Path normalization validation

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0044.md
2. Add input validation for path normalization in config.py and make/discovery.py
3. Run tests: pytest -q tests/test_config_manager.py tests/test_discovery.py
4. Archive task: mv tasks/TASK-0044.md tasks/archive/
5. Commit: "Complete TASK-0044: Add input validation for path normalization"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0048: Type annotations for diagnostics

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0048.md
2. Add type annotations to diagnostic structures in diagnostics.py and make/parser.py
3. Run mypy: mypy gmake2cmake/diagnostics.py gmake2cmake/make/parser.py
4. Run tests: pytest -q tests/test_diagnostics.py
5. Archive task: mv tasks/TASK-0048.md tasks/archive/
6. Commit: "Complete TASK-0048: Add type annotations for diagnostic structures"
"""
    )
]

# Phase 2, Batch 2A - Discovery and Parser (5 agents)
agents_2a = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0012: CLI imports cleanup

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0012.md
2. Clean up imports in gmake2cmake/cli.py
3. Consolidate report serialization logic
4. Run tests: pytest -q tests/test_cli.py
5. Archive task: mv tasks/TASK-0012.md tasks/archive/
6. Commit: "Complete TASK-0012: Clean up CLI imports and report serialization"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0013: UnknownConstruct messaging

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0013.md
2. Improve diagnostic messaging for UnknownConstruct in gmake2cmake/make/evaluator.py
3. Use diagnostic codes from TASK-0025
4. Run tests: pytest -q tests/test_evaluator.py
5. Archive task: mv tasks/TASK-0013.md tasks/archive/
6. Commit: "Complete TASK-0013: Improve UnknownConstruct diagnostic messaging"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0015: Fix -include handling

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0015.md
2. Fix -include handling in gmake2cmake/make/discovery.py
3. Use FileSystemAdapter from TASK-0019
4. Run tests: pytest -q tests/test_discovery.py
5. Archive task: mv tasks/TASK-0015.md tasks/archive/
6. Commit: "Complete TASK-0015: Fix -include handling in discovery"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0030: Recursive Make traversal

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0030.md
2. Handle recursive Make subdirectory traversal in gmake2cmake/make/discovery.py
3. Use FileSystemAdapter from TASK-0019
4. Run tests: pytest -q tests/test_discovery.py
5. Archive task: mv tasks/TASK-0030.md tasks/archive/
6. Commit: "Complete TASK-0030: Handle recursive Make subdirectory traversal"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0045: Refactor parser control flow

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0045.md
2. Refactor control flow in gmake2cmake/make/parser.py
3. Simplify conditional logic and reduce complexity
4. Run tests: pytest -q tests/test_parser.py
5. Archive task: mv tasks/TASK-0045.md tasks/archive/
6. Commit: "Complete TASK-0045: Refactor parser control flow"
"""
    )
]

# Phase 2, Batch 2B - Config and Utilities (3 agents)
agents_2b = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0033: Config schema validation

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0033.md
2. Implement config schema validation in gmake2cmake/config.py
3. Create config_schema.json with JSON schema
4. Run tests: pytest -q tests/test_config_manager.py
5. Archive task: mv tasks/TASK-0033.md tasks/archive/
6. Commit: "Complete TASK-0033: Implement config schema validation"
7. NOTE: Skip TASK-0054 as duplicate
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0036: Standardize exception handling

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0036.md
2. Standardize exception handling in cli.py and config.py
3. Use constants from TASK-0041
4. Run tests: pytest -q tests/test_cli.py tests/test_config_manager.py
5. Archive task: mv tasks/TASK-0036.md tasks/archive/
6. Commit: "Complete TASK-0036: Standardize exception handling"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0046: Logging strategy

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0046.md
2. Implement consistent logging strategy
3. Create gmake2cmake/logging_config.py
4. Run tests: pytest -q tests/ --log-level=DEBUG
5. Archive task: mv tasks/TASK-0046.md tasks/archive/
6. Commit: "Complete TASK-0046: Implement consistent logging strategy"
"""
    )
]

# Phase 3, Batch 3B - IR Builder Features (4 agents)
agents_3b = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0016: Custom commands preservation

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0016.md
2. Preserve custom commands in gmake2cmake/ir/builder.py
3. Update gmake2cmake/cmake/emitter.py to emit custom commands
4. Run tests: pytest -q tests/ir/test_ir_builder.py tests/emitter/test_emitter.py
5. Archive task: mv tasks/TASK-0016.md tasks/archive/
6. Commit: "Complete TASK-0016: Preserve custom commands through IR and emitter"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0017: Target mapping visibility

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0017.md
2. Honor target mapping link libs and visibility in gmake2cmake/ir/builder.py
3. Update gmake2cmake/cmake/emitter.py to respect visibility
4. Run tests: pytest -q tests/ir/test_ir_builder.py tests/emitter/test_emitter.py
5. Archive task: mv tasks/TASK-0017.md tasks/archive/
6. Commit: "Complete TASK-0017: Honor target mapping link libs and visibility"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0022: Pattern rule instantiation

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0022.md
2. Handle pattern rule instantiation in gmake2cmake/ir/builder.py
3. Use FileSystemAdapter and ordering utilities
4. Run tests: pytest -q tests/ir/test_pattern_instantiation.py
5. Archive task: mv tasks/TASK-0022.md tasks/archive/
6. Commit: "Complete TASK-0022: Handle pattern rule instantiation in IRBuilder"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0023: Cycle detection

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0023.md
2. Implement target dependency cycle detection in gmake2cmake/ir/builder.py
3. Use ordering utilities from TASK-0031
4. Run tests: pytest -q tests/ir/test_dependency_cycles.py
5. Archive task: mv tasks/TASK-0023.md tasks/archive/
6. Commit: "Complete TASK-0023: Implement target dependency cycle detection"
"""
    )
]

# Phase 4, Batch 4B - Advanced Features (3 agents)
agents_4b = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0021: Multiprocessing support

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0021.md
2. Add multiprocessing support to gmake2cmake/make/evaluator.py
3. Ensure deterministic output with parallel evaluation
4. Run tests: pytest -q tests/test_parallel_evaluation.py -n auto
5. Archive task: mv tasks/TASK-0021.md tasks/archive/
6. Commit: "Complete TASK-0021: Add multiprocessing support for parallel evaluation"
WARNING: High risk - test thoroughly for concurrency bugs
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0032: Markdown report generator

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0032.md
2. Create gmake2cmake/diagnostics/markdown_reporter.py
3. Implement Markdown report format and generator
4. Run tests: pytest -q tests/diagnostics/test_markdown_report.py
5. Archive task: mv tasks/TASK-0032.md tasks/archive/
6. Commit: "Complete TASK-0032: Define Markdown report format and generator"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0052: CLI exit code strategy

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0052.md
2. Implement richer CLI exit code strategy in gmake2cmake/cli.py
3. Use diagnostic codes from TASK-0025
4. Run tests: pytest -q tests/test_cli.py
5. Archive task: mv tasks/TASK-0052.md tasks/archive/
6. Commit: "Complete TASK-0052: Implement richer CLI exit code strategy"
"""
    )
]

# Phase 5, Batch 5A - Final Polish (3 agents)
agents_5a = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0027: CLI help system

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0027.md
2. Add comprehensive CLI help system to gmake2cmake/cli.py
3. Create docs/ with usage examples
4. Run: gmake2cmake --help
5. Archive task: mv tasks/TASK-0027.md tasks/archive/
6. Commit: "Complete TASK-0027: Add comprehensive CLI help system"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0026: Integration test scenarios

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0026.md
2. Implement comprehensive integration test scenarios in tests/integration/
3. Cover all 26 scenarios from Architecture.md (TS01-TS26)
4. Run tests: pytest -q tests/integration/test_scenarios.py -v --scenario=all
5. Archive task: mv tasks/TASK-0026.md tasks/archive/
6. Commit: "Complete TASK-0026: Implement comprehensive integration test scenarios"
"""
    ),
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt="""Execute TASK-0053: Performance profiling

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0053.md
2. Add performance profiling to all pipeline modules
3. Create profiling utilities and benchmarks
4. Run benchmarks and document results
5. Archive task: mv tasks/TASK-0053.md tasks/archive/
6. Commit: "Complete TASK-0053: Add performance profiling and optimization"
"""
    )
]
</parallel_commands>

### Sequential Execution Commands
<sequential_commands>
# Phase 1, Batch 1C - Filesystem Foundation (Sequential)
# CRITICAL: High-risk infrastructure task affecting all modules

Step 1: Execute TASK-0019
agent_1c_1 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0019: FileSystemAdapter interface

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0019.md
2. Create gmake2cmake/filesystem.py with FileSystemAdapter interface
3. Update all modules to use adapter (discovery, parser, evaluator, etc.)
4. Run tests: pytest -q tests/test_filesystem.py tests/test_discovery.py tests/test_integration*.py
5. Archive task: mv tasks/TASK-0019.md tasks/archive/
6. Commit: "Complete TASK-0019: Define and implement FileSystemAdapter interface"

WARNING: This is a HIGH RISK task affecting ALL modules. Test thoroughly before proceeding.
"""
)

# Wait for TASK-0019 completion and validation before proceeding

Step 2: Execute TASK-0042
agent_1c_2 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0042: FileSystem error handling

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0042.md
2. Document and harden error handling in gmake2cmake/fs.py
3. Use FileSystemAdapter from TASK-0019
4. Run tests: pytest -q tests/test_filesystem.py
5. Archive task: mv tasks/TASK-0042.md tasks/archive/
6. Commit: "Complete TASK-0042: Document and harden FileSystem error handling"
"""
)

# Phase 2, Batch 2C - Evaluator Enhancements (Sequential)
# Must run in order due to dependencies

Step 1: Execute TASK-0049
agent_2c_1 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0049: Context managers

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0049.md
2. Add context managers for resource handling in fs.py and cli.py
3. Use FileSystemAdapter from TASK-0019
4. Run tests: pytest -q tests/test_filesystem.py tests/test_cli.py
5. Archive task: mv tasks/TASK-0049.md tasks/archive/
6. Commit: "Complete TASK-0049: Add context managers for resource handling"
"""
)

Step 2: Execute TASK-0028
agent_2c_2 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0028: Recursive loop detection

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0028.md
2. Implement recursive variable loop detection in gmake2cmake/make/evaluator.py
3. Use diagnostic codes from TASK-0025
4. Run tests: pytest -q tests/test_evaluator.py
5. Archive task: mv tasks/TASK-0028.md tasks/archive/
6. Commit: "Complete TASK-0028: Implement recursive variable loop detection"
"""
)

Step 3: Execute TASK-0020
agent_2c_3 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0020: Caching layer

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0020.md
2. Implement caching layer for MakeEvaluator
3. Create gmake2cmake/cache.py
4. Run tests: pytest -q tests/test_evaluator.py
5. Verify: Caching provides speedup without changing output
6. Archive task: mv tasks/TASK-0020.md tasks/archive/
7. Commit: "Complete TASK-0020: Implement caching layer for MakeEvaluator"
"""
)

Step 4: Execute TASK-0029
agent_2c_4 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0029: Complex Make functions

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0029.md
2. Support complex Make functions in gmake2cmake/make/evaluator.py
3. Use diagnostic codes from TASK-0025
4. Run tests: pytest -q tests/test_evaluator.py
5. Archive task: mv tasks/TASK-0029.md tasks/archive/
6. Commit: "Complete TASK-0029: Support complex Make functions"
"""
)

# Phase 3, Batch 3A - IR Builder Base (Sequential)
# Must run in order to establish foundation

Step 1: Execute TASK-0038
agent_3a_1 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0038: Fix alias assignment

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0038.md
2. Fix redundant alias assignment logic in gmake2cmake/ir/builder.py
3. Use constants from TASK-0037
4. Run tests: pytest -q tests/ir/test_ir_builder.py
5. Archive task: mv tasks/TASK-0038.md tasks/archive/
6. Commit: "Complete TASK-0038: Fix redundant alias assignment logic"
"""
)

Step 2: Execute TASK-0047
agent_3a_2 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0047: Optimize set merges

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0047.md
2. Optimize repeated set merges in build_targets (gmake2cmake/ir/builder.py)
3. Run tests: pytest -q tests/ir/test_ir_builder.py
4. Verify: Performance improvement without behavior change
5. Archive task: mv tasks/TASK-0047.md tasks/archive/
6. Commit: "Complete TASK-0047: Optimize repeated set merges in build_targets"
"""
)

Step 3: Execute TASK-0018
agent_3a_3 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0018: Global config normalization

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0018.md
2. Normalize global config with flag mapping in gmake2cmake/ir/builder.py and config.py
3. Use constants from TASK-0041 and exception handling from TASK-0036
4. Run tests: pytest -q tests/ir/test_ir_builder.py tests/test_config_manager.py
5. Archive task: mv tasks/TASK-0018.md tasks/archive/
6. Commit: "Complete TASK-0018: Normalize global config with flag mapping"
"""
)

# Phase 4, Batch 4A - Emitter Updates (Sequential)
agent_4a = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0014: Detect unmappable constructs

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0014.md
2. Detect unmappable constructs in gmake2cmake/cmake/emitter.py
3. Update gmake2cmake/ir/unknowns.py as needed
4. Use constants from TASK-0037 and TASK-0041
5. Ensure emitter handles TASK-0016, TASK-0017, TASK-0018 changes
6. Run tests: pytest -q tests/emitter/ tests/ir/ tests/test_integration*.py
7. Archive task: mv tasks/TASK-0014.md tasks/archive/
8. Commit: "Complete TASK-0014: Detect unmappable constructs in CMakeEmitter"
"""
)

# Phase 4, Batch 4C - Validation and Error Recovery (Sequential)
Step 1: Execute TASK-0050
agent_4c_1 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0050: Dataclass validation

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0050.md
2. Add validation to core dataclasses in config.py, cli.py, ir/ modules
3. Run tests: pytest -q tests/test_config_manager.py tests/test_cli.py tests/ir/
4. Archive task: mv tasks/TASK-0050.md tasks/archive/
5. Commit: "Complete TASK-0050: Add validation to core dataclasses"
"""
)

Step 2: Execute TASK-0024
agent_4c_2 = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="""Execute TASK-0024: Error recovery strategy

1. Read task file: /home/vfeenstr/devel/prompt-engineering/tasks/TASK-0024.md
2. Implement error recovery and partial conversion across all pipeline components
3. Update discovery, parser, evaluator, IR builder, emitter
4. Run tests: pytest -q tests/test_error_recovery.py tests/ --maxfail=1
5. Archive task: mv tasks/TASK-0024.md tasks/archive/
6. Commit: "Complete TASK-0024: Implement error recovery and partial conversion"

CRITICAL: This task requires most pipeline tasks to be complete. Validate thoroughly.
"""
)
</sequential_commands>

## Quality Gates

### Pre-Execution Checklist
<pre_execution>
- [ ] Working tree clean (git status shows no uncommitted changes)
- [ ] All tests passing (pytest -q tests/)
- [ ] Dependencies installed (pip install -e .[dev])
- [ ] Backup created (git branch backup-$(date +%Y%m%d))
- [ ] Python version 3.8+ confirmed
- [ ] Haiku model access verified for Task tool
- [ ] Task files present (ls tasks/TASK-*.md shows 43 files)
- [ ] No merge conflicts in tasks/ directory
</pre_execution>

### Per-Task Validation
<per_task_validation>
**For each task, the agent must:**

1. **Read task file**: Confirm task requirements and acceptance criteria
2. **Implement changes**: Make code modifications as specified
3. **Run task-specific tests**: Execute tests relevant to changed modules
   ```bash
   pytest -q tests/test_<module>.py
   ```
4. **Verify no test breakage**: Ensure all tests pass
   ```bash
   pytest -q tests/
   ```
5. **Check file modifications**: Verify only intended files changed
   ```bash
   git diff --stat
   ```
6. **Archive task**: Move task file to archive directory
   ```bash
   mv tasks/TASK-XXXX.md tasks/archive/
   ```
7. **Commit changes**: Create atomic commit with descriptive message
   ```bash
   git add -A
   git commit -m "Complete TASK-XXXX: [summary]"
   ```

**Validation Checklist per Task:**
- [ ] Task file read and understood
- [ ] Implementation matches task requirements
- [ ] Task-specific tests pass
- [ ] Full test suite passes (no regressions)
- [ ] Code quality checks pass (ruff, mypy as applicable)
- [ ] Task file archived to tasks/archive/
- [ ] Changes committed with proper message format
- [ ] No unintended side effects observed
</per_task_validation>

### Phase Validation
<phase_validation>
**After each phase (1-5), perform comprehensive validation:**

1. **Run full test suite:**
   ```bash
   pytest -q tests/ -v
   ```
   - Verify: All tests pass (100% success rate)
   - Check: No new warnings or deprecations
   - Confirm: Test coverage maintained or improved

2. **Run code quality checks:**
   ```bash
   ruff check .
   mypy gmake2cmake/
   ```
   - Verify: No new linting errors
   - Check: Type checking passes
   - Confirm: Import ordering consistent

3. **Run integration tests:**
   ```bash
   pytest -q tests/test_integration*.py
   ```
   - Verify: End-to-end scenarios pass
   - Check: Pipeline produces valid CMake output
   - Confirm: No regressions in core functionality

4. **Review changes:**
   ```bash
   git log --oneline --since="1 phase ago"
   git diff HEAD~N..HEAD --stat
   ```
   - Verify: All expected tasks completed
   - Check: Commits follow format "Complete TASK-XXXX: [summary]"
   - Confirm: Tasks archived correctly

5. **Document issues:**
   - Record any test failures or unexpected behavior
   - Note performance changes (improvements or regressions)
   - Track technical debt introduced (if any)

**Phase Checklist:**
- [ ] Full test suite passes (pytest -q tests/)
- [ ] Code quality checks pass (ruff, mypy)
- [ ] Integration tests pass
- [ ] All tasks in phase archived
- [ ] All tasks in phase committed
- [ ] No unresolved merge conflicts
- [ ] Performance acceptable
- [ ] Documentation updated if needed
</phase_validation>

### Checkpoint Commands
<checkpoint_commands>
# After Phase 1 (Foundation)
pytest -q tests/
ruff check .
mypy gmake2cmake/
git log --oneline --since="Phase 1 start"

# After Phase 2 (Module Improvements)
pytest -q tests/test_discovery.py tests/test_parser.py tests/test_evaluator.py
pytest -q tests/test_config_manager.py tests/test_cli.py
ruff check .

# After Phase 3 (IR Builder)
pytest -q tests/ir/
pytest -q tests/emitter/
pytest -q tests/test_integration*.py

# After Phase 4 (Emitter and Advanced)
pytest -q tests/test_error_recovery.py
pytest -q tests/test_parallel_evaluation.py -n auto
pytest -q tests/

# After Phase 5 (Testing and Documentation)
pytest -q tests/integration/test_scenarios.py -v --scenario=all
pytest -q tests/ --cov=gmake2cmake --cov-report=html
gmake2cmake --help
gmake2cmake --version
</checkpoint_commands>

## Failure Recovery

### Rollback Procedures
<rollback>
**If task fails during execution:**

1. **Identify failure point:**
   ```bash
   pytest -q tests/ --tb=short
   git status
   git diff
   ```

2. **Assess damage:**
   - Determine if failure is task-specific or systemic
   - Check if tests were passing before task
   - Verify no corrupted files or broken imports

3. **Rollback options:**

   **Option A: Revert last commit (if task was committed)**
   ```bash
   git log -1  # Confirm commit to revert
   git revert HEAD
   pytest -q tests/  # Verify tests pass
   ```

   **Option B: Discard uncommitted changes**
   ```bash
   git restore .
   git clean -fd
   pytest -q tests/  # Verify tests pass
   ```

   **Option C: Reset to last known good state**
   ```bash
   git log --oneline  # Find last good commit
   git reset --hard <commit-hash>
   pytest -q tests/  # Verify tests pass
   ```

4. **Document failure:**
   - Add note to task file explaining failure
   - Update task status (e.g., "Blocked by: <issue>")
   - Create GitHub issue if needed

5. **Continue or skip:**
   - If task is blocking, resolve issue before continuing
   - If task is non-critical, mark as skipped and continue with next batch
   - If task is in parallel batch, continue with other tasks

**Recovery Checklist:**
- [ ] Failure identified and documented
- [ ] Code rolled back to stable state
- [ ] Tests passing after rollback
- [ ] Failure cause understood
- [ ] Decision made: retry, skip, or block
- [ ] Team notified if blocking issue
</rollback>

### Skip Conditions
<skip_conditions>
**Skip a task if any of the following conditions are met:**

1. **Duplicate task identified:**
   - Example: TASK-0043 duplicates TASK-0025 (both create diagnostic registry)
   - Example: TASK-0054 duplicates TASK-0033 (both add config schema validation)
   - Action: Document duplication in task file, archive without implementation

2. **Blocking dependency unavailable:**
   - Example: TASK-0037 requires TASK-0041 (constants) to be complete
   - Action: Wait for dependency or defer to later batch

3. **Task requirements unclear:**
   - Acceptance criteria ambiguous or contradictory
   - Scope undefined or overlapping with other tasks
   - Action: Request clarification from stakeholders before proceeding

4. **High-risk task requires review:**
   - Task affects critical path (FileSystemAdapter, error recovery)
   - Task has potential for widespread breakage
   - Action: Defer to manual review and implementation

5. **Test infrastructure missing:**
   - Task requires tests that don't exist yet
   - Test fixtures or mocks not available
   - Action: Create test infrastructure first or defer task

6. **External dependency unavailable:**
   - Required library or tool not installed
   - API or service not accessible
   - Action: Install dependencies or defer until available

**Skip Protocol:**
1. Add "SKIP:" prefix to task file name: `TASK-0043.md` → `SKIP-TASK-0043.md`
2. Document skip reason in task file
3. Archive to `tasks/archive/skipped/`
4. Continue with next task in batch
5. Review skipped tasks at end of phase
</skip_conditions>

### Partial Completion Strategy
<partial_completion>
**If batch partially completes (some tasks succeed, some fail):**

1. **Identify successful tasks:**
   ```bash
   git log --oneline --since="Batch start"
   ls tasks/archive/ | grep "TASK-00"
   ```

2. **Validate successful tasks:**
   ```bash
   pytest -q tests/  # Ensure no regressions from successful tasks
   ```

3. **Isolate failed tasks:**
   - Move failed task files to `tasks/failed/`
   - Document failure reasons
   - Assess impact on downstream dependencies

4. **Decision matrix:**
   - **If failed task is blocking:** Pause phase, resolve failure, retry
   - **If failed task is non-blocking:** Continue with next batch, revisit later
   - **If failed task is in parallel batch:** Continue with other parallel tasks
   - **If multiple tasks fail:** Assess systemic issue, may need to pause entire phase

5. **Adjust execution plan:**
   - Update dependency graph for remaining tasks
   - Re-evaluate parallel batches (remove blocked tasks)
   - Consider alternative implementation approaches

**Partial Completion Checklist:**
- [ ] Successful tasks validated and committed
- [ ] Failed tasks identified and documented
- [ ] Impact assessment complete
- [ ] Execution plan adjusted
- [ ] Team notified of status
- [ ] Decision made: continue, pause, or pivot
</partial_completion>

## Code Review Preparation

### Review Checklist
<review_prep>
**Before requesting code review, ensure:**

- [ ] **All tasks completed:** 41 unique tasks successfully implemented (excluding 2 duplicates)
- [ ] **Tests passing:** Full test suite passes with no failures
  ```bash
  pytest -q tests/ -v
  ```
- [ ] **Code quality:** Linting and type checking pass
  ```bash
  ruff check .
  mypy gmake2cmake/
  ```
- [ ] **Integration tests:** All 26 scenarios pass
  ```bash
  pytest -q tests/integration/test_scenarios.py -v --scenario=all
  ```
- [ ] **Coverage target:** Code coverage meets or exceeds 80%
  ```bash
  pytest --cov=gmake2cmake --cov-report=html
  ```
- [ ] **Documentation:** All public APIs documented with docstrings
- [ ] **Changelog:** Update CHANGELOG.md with summary of changes
- [ ] **Commits organized:** Logical, atomic commits with clear messages
  ```bash
  git log --oneline --since="Execution start"
  ```
- [ ] **No debug code:** Remove print statements, debug flags, commented code
- [ ] **No TODOs:** Resolve or document all TODO comments
- [ ] **Architecture alignment:** Changes follow project architecture
- [ ] **Performance:** No significant performance regressions
  ```bash
  pytest --benchmark
  ```

**Review Artifacts:**
- Full test output (pytest report)
- Coverage report (HTML)
- Linting report (ruff output)
- Type checking report (mypy output)
- Integration test results
- Performance benchmarks (if available)
- Summary document listing all completed tasks
</review_prep>

### Change Grouping
<change_grouping>
**Organize changes into logical review units:**

**Group 1: Infrastructure (Phase 1)**
- Constants centralization
- Diagnostic code registry
- Ordering utilities
- FileSystemAdapter interface
- Code quality improvements (docstrings, imports, type hints)

**Group 2: Module Refactoring (Phase 2)**
- CLI cleanup and improvements
- Config schema validation
- Discovery enhancements (-include, recursive Make)
- Parser refactoring
- Evaluator enhancements (caching, loop detection, functions)
- Error handling and logging

**Group 3: IR Builder (Phase 3)**
- Base improvements (alias assignment, set optimization, config normalization)
- Feature additions (custom commands, target visibility, pattern rules, cycle detection)

**Group 4: Emitter and Advanced (Phase 4)**
- Emitter updates (unmappable constructs)
- Advanced features (multiprocessing, error recovery, dataclass validation)
- Reporting (Markdown reports, exit codes)

**Group 5: Testing and Documentation (Phase 5)**
- Integration test scenarios
- CLI help system
- Performance profiling

**Review Approach:**
- Review groups sequentially (foundation → advanced)
- Focus on high-risk changes (FileSystemAdapter, multiprocessing, error recovery)
- Validate each group independently
- Ensure no cross-group conflicts
</change_grouping>

### Documentation Updates
<documentation_updates>
**Update documentation to reflect changes:**

1. **README.md:**
   - Update feature list with new capabilities
   - Add examples for new flags/options
   - Update installation instructions if needed

2. **CHANGELOG.md:**
   - Add section for this release
   - Summarize all 41 implemented tasks by category
   - Note breaking changes (if any)
   - Credit contributors

3. **Architecture.md:**
   - Update architecture diagrams if structure changed
   - Document new modules (filesystem.py, constants.py, etc.)
   - Update component descriptions

4. **API Documentation:**
   - Generate or update API docs from docstrings
   - Document new public interfaces
   - Update examples

5. **Developer Guide:**
   - Document new test scenarios
   - Update contribution guidelines
   - Add debugging tips for new features

**Documentation Checklist:**
- [ ] README.md updated
- [ ] CHANGELOG.md entry added
- [ ] Architecture.md reflects current state
- [ ] API documentation generated
- [ ] Developer guide updated
- [ ] All links and references valid
</documentation_updates>

### Test Evidence
<test_evidence>
**Capture and document test results:**

1. **Full test suite:**
   ```bash
   pytest -q tests/ -v > test_results.txt 2>&1
   ```
   - Attach: test_results.txt
   - Summary: Total tests, pass rate, duration

2. **Integration tests:**
   ```bash
   pytest -q tests/integration/test_scenarios.py -v --scenario=all > integration_results.txt 2>&1
   ```
   - Attach: integration_results.txt
   - Summary: All 26 scenarios pass

3. **Coverage report:**
   ```bash
   pytest --cov=gmake2cmake --cov-report=html --cov-report=term > coverage_results.txt 2>&1
   ```
   - Attach: htmlcov/ directory
   - Summary: Overall coverage percentage, uncovered lines

4. **Code quality:**
   ```bash
   ruff check . > ruff_results.txt 2>&1
   mypy gmake2cmake/ > mypy_results.txt 2>&1
   ```
   - Attach: ruff_results.txt, mypy_results.txt
   - Summary: No errors, no warnings

5. **Performance benchmarks:**
   ```bash
   pytest --benchmark > benchmark_results.txt 2>&1
   ```
   - Attach: benchmark_results.txt
   - Summary: Performance metrics, comparison to baseline

**Test Evidence Checklist:**
- [ ] Full test results captured
- [ ] Integration test results captured
- [ ] Coverage report generated
- [ ] Code quality reports captured
- [ ] Performance benchmarks captured (if available)
- [ ] All evidence attached to PR or review request
</test_evidence>

## Implementation Timeline

<timeline>
**Estimated execution time based on task complexity and dependencies:**

### Phase 1: Foundation Infrastructure
- **Parallel Batch 1A** (3 tasks): 2-3 hours
- **Validation 1A**: 30 minutes
- **Parallel Batch 1B** (5 tasks): 3-4 hours
- **Validation 1B**: 30 minutes
- **Sequential Batch 1C** (2 tasks, high-risk): 4-6 hours
- **Validation 1C**: 1 hour
- **Parallel Batch 1D** (3 tasks): 2-3 hours
- **Validation 1D**: 30 minutes
- **Phase 1 Total**: 13-18 hours (1.5-2 days with testing)

### Phase 2: Module-Specific Improvements
- **Parallel Batch 2A** (5 tasks): 4-6 hours
- **Validation 2A**: 30 minutes
- **Parallel Batch 2B** (3 tasks): 2-3 hours
- **Validation 2B**: 30 minutes
- **Sequential Batch 2C** (4 tasks): 4-6 hours
- **Validation 2C**: 1 hour
- **Phase 2 Total**: 11-17 hours (1.5-2 days with testing)

### Phase 3: IR Builder Core
- **Sequential Batch 3A** (3 tasks): 3-5 hours
- **Validation 3A**: 30 minutes
- **Parallel Batch 3B** (4 tasks): 5-8 hours
- **Validation 3B**: 1 hour
- **Phase 3 Total**: 9-14 hours (1-2 days with testing)

### Phase 4: Emitter and Advanced Features
- **Sequential Batch 4A** (1 task): 2-3 hours
- **Validation 4A**: 1 hour
- **Parallel Batch 4B** (3 tasks, includes high-risk multiprocessing): 6-8 hours
- **Validation 4B**: 1 hour
- **Sequential Batch 4C** (2 tasks, high-risk): 5-8 hours
- **Validation 4C**: 1 hour
- **Phase 4 Total**: 16-23 hours (2-3 days with testing)

### Phase 5: Testing and Documentation
- **Parallel Batch 5A** (3 tasks): 6-8 hours
- **Final Validation**: 2 hours
- **Phase 5 Total**: 8-10 hours (1 day with comprehensive testing)

### Code Review and Documentation
- **Documentation updates**: 2-3 hours
- **Code review preparation**: 1-2 hours
- **Review and revisions**: 4-8 hours
- **Review Total**: 7-13 hours (1-2 days)

### **Grand Total Estimate**
- **Implementation**: 57-82 hours (7-10 working days)
- **Review and polish**: 7-13 hours (1-2 days)
- **Total elapsed**: 64-95 hours (8-12 working days with testing)

**Notes on Estimates:**
- Assumes single developer executing tasks sequentially within parallel batches
- With true parallel execution (multiple developers), could reduce by 40-50%
- High-risk tasks (TASK-0019, TASK-0021, TASK-0024) padded for extra testing
- Integration testing time included in phase validations
- Does not include time for addressing review feedback
</timeline>

<metadata>
<confidence>high</confidence>
<dependencies>
- Research findings from 001-task-execution-research/task-execution-research.md
- Clean working tree (no uncommitted changes)
- Test suite functional and comprehensive
- Haiku model access for Task tool
- Python 3.8+ with pytest, ruff, mypy installed
- Git operations allowed for archiving and committing
</dependencies>
<open_questions>
- Should TASK-0043 be merged with TASK-0025 (both create diagnostic registries)? **Answer**: Yes, skip TASK-0043 as duplicate
- Should TASK-0054 be dropped (duplicate of TASK-0033)? **Answer**: Yes, skip TASK-0054 as duplicate
- What is target code coverage for TASK-0051? **Assumed**: 80%+ based on best practices
- Are baseline benchmarks available for performance tasks? **Assumed**: Will establish baseline during implementation
- Should FileSystemAdapter integration be gradual or all-at-once? **Recommendation**: All-at-once in dedicated sequential batch with extensive testing
- How many parallel agents should be used? **Recommendation**: Align with parallel batch sizes (3-5 agents per batch)
</open_questions>
<assumptions>
- Test suite exists and is reasonably comprehensive for core modules
- CI/CD can run test checkpoints automatically
- Task tool supports haiku model for all agents
- Existing code follows consistent style (imports, naming, etc.)
- TASK-0033 and TASK-0054 are duplicates (both describe config schema validation)
- TASK-0025 and TASK-0043 overlap significantly (both centralize diagnostic codes)
- High-risk tasks will require extra review and testing time
- Integration test scenarios reference Architecture.md TS01-TS26
- All task files are well-defined with clear acceptance criteria
- Git commit access available for archiving and committing
</assumptions>
</metadata>
