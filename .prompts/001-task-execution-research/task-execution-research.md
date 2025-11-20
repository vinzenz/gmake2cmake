# Task Execution Research

## Executive Summary

This document analyzes 43 tasks (TASK-0012 through TASK-0054) for the gmake2cmake project, identifying dependencies, parallelization opportunities, and optimal execution strategies. The tasks cover code quality improvements spanning refactoring, type safety, error handling, performance optimization, and feature enhancements.

Key findings:
- **43 total tasks** covering CLI, config, diagnostics, discovery, parser, evaluator, IR builder, emitter, and infrastructure
- **5 execution layers** identified based on dependencies
- **38% of tasks** can execute in parallel (Layer 0)
- **Critical path**: Constants/infrastructure tasks block many others
- **Highest risk**: Tasks touching evaluator, IR builder, and emitter (core pipeline components)
- **Estimated execution time**: 3-5 phases with test checkpoints

## Task Inventory

| Task ID | Summary | Affected Modules | Risk Level |
|---------|---------|------------------|------------|
| TASK-0012 | Clean up CLI imports and report serialization | cli.py | Low |
| TASK-0013 | Improve UnknownConstruct diagnostic messaging | make/evaluator.py | Low |
| TASK-0014 | Detect unmappable constructs in CMakeEmitter | cmake/emitter.py, ir/unknowns.py | Medium |
| TASK-0015 | Fix -include handling in discovery | make/discovery.py | Medium |
| TASK-0016 | Preserve custom commands through IR and emitter | ir/builder.py, cmake/emitter.py | High |
| TASK-0017 | Honor target mapping link libs and visibility | ir/builder.py, cmake/emitter.py | High |
| TASK-0018 | Normalize global config with flag mapping | ir/builder.py, config.py | Medium |
| TASK-0019 | Define and implement FileSystemAdapter interface | filesystem.py (new), all modules | High |
| TASK-0020 | Implement caching layer for MakeEvaluator | cache.py (new), make/evaluator.py | Medium |
| TASK-0021 | Add multiprocessing support for parallel evaluation | make/evaluator.py | High |
| TASK-0022 | Handle pattern rule instantiation in IRBuilder | ir/builder.py | Medium |
| TASK-0023 | Implement target dependency cycle detection | ir/builder.py | Medium |
| TASK-0024 | Implement error recovery and partial conversion | All pipeline components | High |
| TASK-0025 | Create centralized diagnostic code registry | diagnostics/codes.py (new), all modules | Medium |
| TASK-0026 | Implement comprehensive integration test scenarios | tests/integration/ | Low |
| TASK-0027 | Add comprehensive CLI help system | cli.py, docs/ | Low |
| TASK-0028 | Implement recursive variable loop detection | make/evaluator.py | Medium |
| TASK-0029 | Support complex Make functions | make/evaluator.py | High |
| TASK-0030 | Handle recursive Make subdirectory traversal | make/discovery.py | Medium |
| TASK-0031 | Implement deterministic ordering utilities | utils/ordering.py (new), all modules | Medium |
| TASK-0032 | Define Markdown report format and generator | diagnostics/markdown_reporter.py (new) | Low |
| TASK-0033 | Implement config schema validation | config.py, config_schema.json (new) | Low |
| TASK-0034 | Resolve empty __all__ declaration | __init__.py | Low |
| TASK-0035 | Add missing type hints in CLI helpers | cli.py | Low |
| TASK-0036 | Standardize exception handling | cli.py, config.py | Medium |
| TASK-0037 | Extract magic numbers to named constants | ir/unknowns.py | Low |
| TASK-0038 | Fix redundant alias assignment logic | ir/builder.py | Low |
| TASK-0039 | Add docstrings to public dataclasses | All modules | Low |
| TASK-0040 | Standardize import ordering and style | All modules | Low |
| TASK-0041 | Centralize default values and constants | constants.py (new), all modules | Medium |
| TASK-0042 | Document and harden FileSystem error handling | fs.py | Low |
| TASK-0043 | Centralize and validate diagnostic codes | diagnostic_codes.py (new), all modules | Medium |
| TASK-0044 | Add input validation for path normalization | config.py, make/discovery.py | Low |
| TASK-0045 | Refactor parser control flow | make/parser.py | Medium |
| TASK-0046 | Implement consistent logging strategy | logging_config.py (new), all modules | Low |
| TASK-0047 | Optimize repeated set merges in build_targets | ir/builder.py | Low |
| TASK-0048 | Add type annotations for diagnostic structures | diagnostics.py, make/parser.py | Low |
| TASK-0049 | Add context managers for resource handling | fs.py, cli.py | Low |
| TASK-0050 | Add validation to core dataclasses | config.py, cli.py, ir/ modules | Medium |
| TASK-0051 | Define test coverage strategy | pyproject.toml, tests/ | Low |
| TASK-0052 | Implement richer CLI exit code strategy | cli.py | Low |
| TASK-0053 | Add performance profiling and optimization | All pipeline modules | Low |
| TASK-0054 | Add configuration schema validation | config.py, config_schema.py (new) | Low |

## Dependency Graph

<dependency_analysis>

### File-Based Dependencies

**Constants and Infrastructure (Foundational)**
- TASK-0041 (constants.py) → Blocks: TASK-0012, TASK-0037, TASK-0043
- TASK-0025 (diagnostic_codes.py) → Blocks: TASK-0043, TASK-0013, TASK-0014, TASK-0024
- TASK-0031 (ordering.py) → Blocks: TASK-0023, TASK-0022, TASK-0047
- TASK-0019 (FileSystemAdapter) → Blocks: TASK-0042, TASK-0049, TASK-0015, TASK-0030

**CLI Module (gmake2cmake/cli.py)**
- TASK-0041 → TASK-0012 → TASK-0027
- TASK-0041 → TASK-0035
- TASK-0036 affects TASK-0012, TASK-0052
- TASK-0049 affects TASK-0012

**Config Module (gmake2cmake/config.py)**
- TASK-0041 → TASK-0018
- TASK-0036 affects TASK-0018, TASK-0033, TASK-0054
- TASK-0044 affects TASK-0018
- TASK-0033 and TASK-0054 are duplicates (schema validation)
- TASK-0050 affects TASK-0033/TASK-0054

**Diagnostics Module**
- TASK-0025 → TASK-0043 (both create diagnostic registries - partial duplicate)
- TASK-0043 → TASK-0013, TASK-0014, TASK-0024, TASK-0032
- TASK-0048 affects diagnostics serialization

**Discovery Module (gmake2cmake/make/discovery.py)**
- TASK-0019 → TASK-0015 (FileSystemAdapter needed)
- TASK-0019 → TASK-0030 (recursive make)
- TASK-0044 affects TASK-0015

**Parser Module (gmake2cmake/make/parser.py)**
- TASK-0045 (refactor control flow) - standalone
- TASK-0048 affects TASK-0045 (type annotations)

**Evaluator Module (gmake2cmake/make/evaluator.py)**
- TASK-0013 (diagnostic messaging) - relatively standalone
- TASK-0020 (caching) - can be added later
- TASK-0021 (multiprocessing) depends on TASK-0020 (optional but recommended)
- TASK-0028 (recursive loop detection) - standalone
- TASK-0029 (complex functions) depends on TASK-0025/TASK-0043 (diagnostic codes)

**IR Builder Module (gmake2cmake/ir/builder.py)**
- TASK-0041 → TASK-0037 → TASK-0038 (constants for unknowns)
- TASK-0016 (custom commands)
- TASK-0017 (target mapping)
- TASK-0018 (global config normalization)
- TASK-0022 (pattern rules) depends on TASK-0019 (FileSystemAdapter)
- TASK-0023 (cycle detection) depends on TASK-0031 (ordering utils)
- TASK-0047 (optimize set merges) affects TASK-0017, TASK-0018
- TASK-0050 (validation) affects all IR tasks

**Emitter Module (gmake2cmake/cmake/emitter.py)**
- TASK-0014 (unmappable constructs) depends on TASK-0037/TASK-0041 (constants)
- TASK-0016 (custom commands)
- TASK-0017 (target visibility)
- TASK-0018 (global config)

**Cross-cutting Concerns**
- TASK-0024 (error recovery) affects ALL pipeline modules
- TASK-0039 (docstrings) affects ALL modules
- TASK-0040 (import ordering) affects ALL modules
- TASK-0046 (logging) affects ALL modules
- TASK-0050 (validation) affects config, CLI, IR modules
- TASK-0053 (profiling) affects ALL pipeline modules

**Testing and Documentation**
- TASK-0026 (integration tests) should come after core features stable
- TASK-0027 (CLI help) depends on TASK-0012, TASK-0025/TASK-0043
- TASK-0051 (coverage strategy) - can run anytime
- TASK-0052 (exit codes) depends on TASK-0025/TASK-0043

### Logical Dependencies

1. **Infrastructure First**: Constants, filesystem, diagnostic registry, ordering utils must be established before refactoring other modules
2. **Core Pipeline Order**: Discovery → Parser → Evaluator → IR Builder → Emitter (changes should respect this flow)
3. **Type Safety**: Type hints (TASK-0035, TASK-0048) and validation (TASK-0050) should precede major refactors
4. **Error Handling**: Exception standardization (TASK-0036) and error recovery (TASK-0024) affect all modules
5. **Quality Tools**: Logging (TASK-0046), profiling (TASK-0053), coverage (TASK-0051) are meta-tasks

</dependency_analysis>

## Execution Layers

<execution_layers>

### Layer 0: Foundational Infrastructure (Parallel where possible)
These tasks create new modules or are isolated refactors with no dependencies:

**Group 0A: New Infrastructure Modules (Parallel)**
- TASK-0041: Centralize constants (creates constants.py)
- TASK-0025: Diagnostic code registry (creates diagnostics/codes.py)
- TASK-0031: Deterministic ordering utilities (creates utils/ordering.py)

**Group 0B: Isolated Code Quality (Parallel)**
- TASK-0034: Resolve __all__ declaration (__init__.py only)
- TASK-0035: Add type hints in CLI helpers (cli.py only, no behavior change)
- TASK-0039: Add docstrings (documentation only, no behavior change)
- TASK-0040: Standardize import ordering (formatting only)
- TASK-0051: Define test coverage strategy (test configuration only)

**Group 0C: Filesystem Foundation (Must complete before 0D)**
- TASK-0019: FileSystemAdapter interface (creates filesystem.py, foundational)

**Group 0D: Simple Refactors (After 0C)**
- TASK-0037: Extract magic numbers in unknowns (depends on TASK-0041)
- TASK-0042: FileSystem error handling (depends on TASK-0019)
- TASK-0044: Path normalization validation (relatively isolated)
- TASK-0048: Type annotations for diagnostic dicts (isolated)

### Layer 1: Module-Specific Improvements
These depend on Layer 0 infrastructure but don't affect each other:

**Group 1A: Discovery and Parser (Parallel)**
- TASK-0015: Fix -include handling (depends on TASK-0019, TASK-0041)
- TASK-0030: Recursive Make traversal (depends on TASK-0019)
- TASK-0045: Refactor parser control flow (depends on TASK-0048 optionally)

**Group 1B: Diagnostics and Config (Parallel)**
- TASK-0012: CLI imports cleanup (depends on TASK-0041)
- TASK-0013: UnknownConstruct messaging (depends on TASK-0025, TASK-0037)
- TASK-0033: Config schema validation (depends on TASK-0041)
- TASK-0043: Centralize diagnostic codes (depends on TASK-0025, may be duplicate)
- TASK-0054: Config schema validation (duplicate of TASK-0033)

**Group 1C: Evaluator Enhancements (Sequential within group)**
- TASK-0028: Recursive loop detection (depends on TASK-0025)
- TASK-0020: Caching layer (after TASK-0028)
- TASK-0029: Complex Make functions (depends on TASK-0025, TASK-0043)

**Group 1D: Error Handling (Parallel)**
- TASK-0036: Standardize exception handling (depends on TASK-0041)
- TASK-0046: Logging strategy (relatively independent)
- TASK-0049: Context managers (depends on TASK-0019, TASK-0042)

### Layer 2: IR Builder and Core Features
These tasks modify the IR builder, which is central to the pipeline:

**Group 2A: IR Builder Core (Sequential)**
- TASK-0038: Fix alias assignment (depends on TASK-0037)
- TASK-0047: Optimize set merges (isolated optimization)
- TASK-0018: Global config normalization (depends on TASK-0041, TASK-0036)

**Group 2B: IR Builder Features (Parallel after 2A)**
- TASK-0016: Custom commands preservation (depends on Layer 2A)
- TASK-0017: Target mapping visibility (depends on Layer 2A)
- TASK-0022: Pattern rule instantiation (depends on TASK-0019, TASK-0031)
- TASK-0023: Dependency cycle detection (depends on TASK-0031)

### Layer 3: Emitter and Advanced Features
These depend on IR changes and earlier layers:

**Group 3A: Emitter (Sequential)**
- TASK-0014: Detect unmappable constructs (depends on TASK-0037, TASK-0041)
- Update emitter for TASK-0016 (custom commands)
- Update emitter for TASK-0017 (visibility)
- Update emitter for TASK-0018 (global config)

**Group 3B: Advanced Features (Parallel)**
- TASK-0021: Multiprocessing support (depends on TASK-0020 optionally)
- TASK-0024: Error recovery strategy (depends on most pipeline tasks)
- TASK-0050: Dataclass validation (depends on Layer 2 completion)

**Group 3C: Reporting (Parallel)**
- TASK-0032: Markdown report generator (depends on TASK-0025/TASK-0043)
- TASK-0052: CLI exit code strategy (depends on TASK-0025/TASK-0043)

### Layer 4: Testing and Documentation
Final phase after core functionality stabilized:

**Group 4A: Documentation (Parallel)**
- TASK-0027: CLI help system (depends on TASK-0012, TASK-0025)

**Group 4B: Performance and Testing (Parallel)**
- TASK-0026: Integration test scenarios (depends on all pipeline tasks)
- TASK-0053: Performance profiling (depends on pipeline completion)

</execution_layers>

## Critical Path

The following tasks form the critical path that blocks the most other tasks:

1. **TASK-0041** (Constants) - Blocks 6+ tasks directly
2. **TASK-0025** (Diagnostic registry) - Blocks 8+ tasks
3. **TASK-0031** (Ordering utilities) - Blocks IR builder tasks
4. **TASK-0019** (FileSystemAdapter) - Blocks discovery and filesystem tasks
5. **TASK-0037** (Extract constants in unknowns) - Blocks IR builder and emitter
6. **Layer 2 IR Builder tasks** - Block emitter updates
7. **TASK-0024** (Error recovery) - Requires most pipeline tasks completed

**Recommended Focus**: Complete Layer 0 Groups 0A and 0C as highest priority to unblock downstream work.

## Risk Matrix

<risk_assessment>

### High Risk (Breaking Changes Possible)
- **TASK-0016**: Custom commands preservation - Core IR/emitter changes, may break existing flows
- **TASK-0017**: Target mapping visibility - Changes target model, affects emitter
- **TASK-0019**: FileSystemAdapter interface - Touches ALL modules, high integration risk
- **TASK-0021**: Multiprocessing support - Concurrency bugs, pickle-ability issues
- **TASK-0024**: Error recovery strategy - Cross-cutting, affects all error paths
- **TASK-0029**: Complex Make functions - Parser/evaluator semantic changes

### Medium Risk (Potential Regressions)
- **TASK-0014**: Unmappable constructs detection - Emitter logic changes
- **TASK-0015**: -include handling - Discovery graph changes
- **TASK-0018**: Global config normalization - IR builder changes
- **TASK-0020**: Caching layer - State management complexity
- **TASK-0022**: Pattern rule instantiation - IR builder feature addition
- **TASK-0023**: Cycle detection - Graph algorithm correctness
- **TASK-0025**: Diagnostic registry - Refactor all diagnostic sites
- **TASK-0028**: Recursive loop detection - Evaluator control flow
- **TASK-0030**: Recursive Make traversal - Discovery changes
- **TASK-0031**: Ordering utilities - Affects determinism if incorrect
- **TASK-0036**: Exception handling - Error flow changes
- **TASK-0041**: Centralize constants - Many import changes
- **TASK-0043**: Centralize diagnostic codes - Duplicate of TASK-0025
- **TASK-0045**: Parser refactor - Control flow changes risk bugs
- **TASK-0047**: Optimize set merges - Performance change risk
- **TASK-0050**: Dataclass validation - May reject currently valid inputs

### Low Risk (Isolated or Safe Changes)
- **TASK-0012**: CLI cleanup - Import consolidation only
- **TASK-0013**: Diagnostic messaging - Message text changes
- **TASK-0026**: Integration tests - Test-only additions
- **TASK-0027**: CLI help - Documentation only
- **TASK-0032**: Markdown reports - New feature, no existing impact
- **TASK-0033**: Config schema validation - Optional validation
- **TASK-0034**: __all__ declaration - Package interface cleanup
- **TASK-0035**: Type hints - No runtime behavior change
- **TASK-0037**: Extract constants - Localized refactor
- **TASK-0038**: Fix alias assignment - Targeted bug fix
- **TASK-0039**: Add docstrings - Documentation only
- **TASK-0040**: Import ordering - Formatting only
- **TASK-0042**: FileSystem error handling - Error path improvements
- **TASK-0044**: Path validation - Input validation only
- **TASK-0046**: Logging strategy - Observability addition
- **TASK-0048**: Diagnostic type annotations - Type checking only
- **TASK-0049**: Context managers - Resource management improvements
- **TASK-0051**: Coverage strategy - Test infrastructure
- **TASK-0052**: Exit codes - CLI behavior enhancement
- **TASK-0053**: Performance profiling - Profiling-only additions
- **TASK-0054**: Config schema validation - Duplicate of TASK-0033

</risk_assessment>

## Recommended Execution Strategy

<execution_strategy>

### Phase 1: Foundation (Weeks 1-2)
**Objective**: Establish infrastructure and low-risk code quality improvements

**Batch 1A (Parallel - 3 tasks)**
1. TASK-0041: Centralize constants
2. TASK-0025: Diagnostic code registry
3. TASK-0031: Deterministic ordering utilities

**Checkpoint 1A**: Run full test suite, verify no regressions

**Batch 1B (Parallel - 5 tasks)**
4. TASK-0034: Resolve __all__ declaration
5. TASK-0035: Add CLI type hints
6. TASK-0039: Add docstrings
7. TASK-0040: Standardize imports
8. TASK-0051: Coverage strategy

**Checkpoint 1B**: Run linting and type checking, verify code quality

**Batch 1C (Sequential - 2 tasks)**
9. TASK-0019: FileSystemAdapter interface (foundational, high-risk)
10. TASK-0042: FileSystem error handling

**Checkpoint 1C**: Run filesystem and integration tests

**Batch 1D (Parallel - 3 tasks)**
11. TASK-0037: Extract magic numbers (unknowns)
12. TASK-0044: Path validation
13. TASK-0048: Diagnostic type annotations

**Checkpoint 1D**: Full test suite including discovery tests

### Phase 2: Module Improvements (Weeks 3-4)
**Objective**: Refactor and enhance individual modules

**Batch 2A (Parallel - 5 tasks)**
14. TASK-0012: CLI cleanup
15. TASK-0013: UnknownConstruct messaging
16. TASK-0015: Fix -include handling
17. TASK-0030: Recursive Make traversal
18. TASK-0045: Parser refactor

**Checkpoint 2A**: Test discovery and parser modules

**Batch 2B (Parallel - 4 tasks)**
19. TASK-0033: Config schema validation (skip TASK-0054 as duplicate)
20. TASK-0036: Exception handling
21. TASK-0046: Logging strategy
22. TASK-0049: Context managers

**Checkpoint 2B**: Test config and error handling paths

**Batch 2C (Sequential - 3 tasks)**
23. TASK-0028: Recursive loop detection
24. TASK-0020: Caching layer
25. TASK-0029: Complex Make functions

**Checkpoint 2C**: Test evaluator thoroughly, verify determinism

### Phase 3: IR Builder and Core Features (Weeks 5-6)
**Objective**: Enhance IR builder with critical features

**Batch 3A (Sequential - 3 tasks)**
26. TASK-0038: Fix alias assignment
27. TASK-0047: Optimize set merges
28. TASK-0018: Global config normalization

**Checkpoint 3A**: Test IR builder base functionality

**Batch 3B (Parallel - 4 tasks)**
29. TASK-0016: Custom commands preservation
30. TASK-0017: Target mapping visibility
31. TASK-0022: Pattern rule instantiation
32. TASK-0023: Dependency cycle detection

**Checkpoint 3B**: Full IR builder test suite, verify all features

### Phase 4: Emitter and Advanced Features (Week 7)
**Objective**: Complete emitter updates and advanced features

**Batch 4A (Sequential - 1 task)**
33. TASK-0014: Detect unmappable constructs

**Checkpoint 4A**: Test emitter with all IR changes

**Batch 4B (Parallel - 3 tasks)**
34. TASK-0021: Multiprocessing support
35. TASK-0032: Markdown reports
36. TASK-0052: Exit code strategy

**Checkpoint 4B**: Test parallel execution and reporting

**Batch 4C (Sequential - 2 tasks)**
37. TASK-0050: Dataclass validation
38. TASK-0024: Error recovery strategy (requires most tasks complete)

**Checkpoint 4C**: End-to-end pipeline tests with error scenarios

### Phase 5: Testing and Polish (Week 8)
**Objective**: Comprehensive testing and documentation

**Batch 5A (Parallel - 3 tasks)**
39. TASK-0027: CLI help system
40. TASK-0026: Integration test scenarios
41. TASK-0053: Performance profiling

**Final Checkpoint**: Full test suite, integration scenarios, performance benchmarks

### Notes on Execution Strategy
- **TASK-0043 omitted**: Appears to be a duplicate of TASK-0025 (both create diagnostic code registries)
- **TASK-0054 omitted**: Duplicate of TASK-0033 (both add config schema validation)
- **Checkpoint-driven approach**: Run tests after each batch to catch issues early
- **Parallel execution**: Use multiple developers or branches for parallel batches
- **Risk mitigation**: High-risk tasks isolated with dedicated checkpoints
- **Rollback plan**: Each checkpoint allows reverting to last stable state

</execution_strategy>

## Validation Checkpoints

<checkpoints>

### Checkpoint 1A: After Foundation Infrastructure (Batch 1A)
**Tests to Run:**
```bash
pytest -q tests/
ruff check .
```
**Success Criteria:**
- All existing tests pass
- No new linting errors
- Constants module exports expected values
- Diagnostic codes enum populated
- Ordering utilities functional

### Checkpoint 1B: After Code Quality (Batch 1B)
**Tests to Run:**
```bash
ruff check . --select I,D,ANN
pytest -q tests/ --cov=gmake2cmake --cov-report=term
mypy gmake2cmake/
```
**Success Criteria:**
- Import ordering consistent
- Docstring coverage improved
- Type hints present on public APIs
- Test coverage baseline established

### Checkpoint 1C: After FileSystemAdapter (Batch 1C)
**Tests to Run:**
```bash
pytest -q tests/test_filesystem.py tests/test_discovery.py tests/test_integration*.py
ruff check .
```
**Success Criteria:**
- FileSystemAdapter tests pass
- All components use adapter interface
- No direct filesystem access in core modules
- Discovery tests pass with new adapter

### Checkpoint 1D: After Simple Refactors (Batch 1D)
**Tests to Run:**
```bash
pytest -q tests/test_unknowns.py tests/test_config_manager.py tests/test_diagnostics.py
ruff check .
```
**Success Criteria:**
- Unknowns module uses constants
- Path validation catches invalid inputs
- Diagnostic serialization maintains structure

### Checkpoint 2A: After Discovery and Parser (Batch 2A)
**Tests to Run:**
```bash
pytest -q tests/test_discovery.py tests/test_parser.py tests/test_cli.py
pytest -q tests/test_evaluator.py
```
**Success Criteria:**
- -include handling works correctly
- Recursive make detection functional
- Parser refactor maintains behavior
- CLI cleanup complete with consistent imports

### Checkpoint 2B: After Config and Error Handling (Batch 2B)
**Tests to Run:**
```bash
pytest -q tests/test_config_manager.py tests/test_cli.py
pytest -q tests/ --log-level=DEBUG
```
**Success Criteria:**
- Config schema validation working
- Exception handling targeted and appropriate
- Logging configured correctly
- Context managers provide cleanup

### Checkpoint 2C: After Evaluator Enhancements (Batch 2C)
**Tests to Run:**
```bash
pytest -q tests/test_evaluator.py tests/evaluator/
pytest -q tests/ --benchmark  # if benchmarking available
```
**Success Criteria:**
- Recursive loop detection functional
- Caching provides speedup without changing output
- Complex Make functions supported
- Deterministic output maintained

### Checkpoint 3A: After IR Builder Base (Batch 3A)
**Tests to Run:**
```bash
pytest -q tests/ir/test_ir_builder.py
pytest -q tests/emitter/test_emitter.py
```
**Success Criteria:**
- Alias assignment correct
- Set merge optimization working
- Global config normalization applied
- No regression in IR generation

### Checkpoint 3B: After IR Builder Features (Batch 3B)
**Tests to Run:**
```bash
pytest -q tests/ir/test_ir_builder.py
pytest -q tests/ir/test_pattern_instantiation.py
pytest -q tests/ir/test_dependency_cycles.py
pytest -q tests/emitter/test_emitter.py
```
**Success Criteria:**
- Custom commands preserved in IR and emitted
- Target visibility honored
- Pattern rules instantiated correctly
- Dependency cycles detected and reported
- All IR builder tests pass

### Checkpoint 4A: After Emitter Updates (Batch 4A)
**Tests to Run:**
```bash
pytest -q tests/emitter/
pytest -q tests/ir/
pytest -q tests/test_integration*.py
```
**Success Criteria:**
- Unmappable constructs detected
- UnknownConstruct diagnostics emitted
- CMake output valid for all test cases
- Integration tests pass

### Checkpoint 4B: After Advanced Features (Batch 4B)
**Tests to Run:**
```bash
pytest -q tests/test_parallel_evaluation.py -n auto
pytest -q tests/diagnostics/test_markdown_report.py
pytest -q tests/test_cli.py
```
**Success Criteria:**
- Multiprocessing produces identical output
- Markdown reports generated correctly
- Exit codes reflect diagnostic status
- Performance acceptable with parallelism

### Checkpoint 4C: After Error Recovery (Batch 4C)
**Tests to Run:**
```bash
pytest -q tests/test_error_recovery.py
pytest -q tests/test_config_manager.py
pytest -q tests/test_cli.py
pytest -q tests/ --maxfail=1
```
**Success Criteria:**
- Dataclass validation catches invalid inputs
- Error recovery allows partial conversion
- Pipeline handles errors gracefully
- All tests pass

### Final Checkpoint: After Documentation and Testing (Batch 5A)
**Tests to Run:**
```bash
pytest -q tests/integration/test_scenarios.py -v --scenario=all
pytest -q tests/ --cov=gmake2cmake --cov-report=html
gmake2cmake --help
gmake2cmake --version
gmake2cmake --list-diagnostics
man ./docs/gmake2cmake.1  # if generated
```
**Success Criteria:**
- All 26 integration scenarios pass
- Code coverage meets target (e.g., 80%+)
- CLI help comprehensive and accurate
- Performance benchmarks acceptable
- Documentation complete and correct

</checkpoints>

<metadata>
<confidence>high</confidence>
<dependencies>
- Python 3.8+ with pytest, ruff, mypy
- Test fixtures for Makefile scenarios
- CI/CD pipeline for automated checkpoint validation
- Multiple developers or feature branches for parallel execution
</dependencies>
<open_questions>
- Should TASK-0043 be merged with TASK-0025 (both create diagnostic registries)?
- Should TASK-0054 be dropped (duplicate of TASK-0033)?
- What is the target code coverage percentage for TASK-0051?
- Are there existing benchmarks to validate TASK-0020 (caching) and TASK-0021 (multiprocessing) performance gains?
- What is the desired behavior for TASK-0024 error recovery - continue always or only with flag?
- Should TASK-0019 (FileSystemAdapter) integration be gradual or all-at-once?
</open_questions>
<assumptions>
- Test suite exists and is reasonably comprehensive for core modules
- CI/CD can run test checkpoints automatically
- Developers available for parallel work where identified
- Existing code follows some consistent style (imports, naming, etc.)
- TASK-0033 and TASK-0054 are indeed duplicates (both describe config schema validation)
- TASK-0025 and TASK-0043 overlap significantly (both centralize diagnostic codes)
- High-risk tasks (TASK-0019, TASK-0024) will require extra review and testing time
- Performance tasks (TASK-0020, TASK-0021, TASK-0053) have baseline measurements
- Integration test scenarios (TASK-0026) reference Architecture.md TS01-TS26
</assumptions>
</metadata>
