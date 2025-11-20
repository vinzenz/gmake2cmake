# Test Coverage Strategy

This document outlines the test coverage goals and current status of the gmake2cmake project.

## Coverage Configuration

Coverage is configured in `pyproject.toml` with the following settings:

- **Source**: `gmake2cmake` package (all production code)
- **Branch Coverage**: Enabled for detailed conditional branch tracking
- **Omissions**: Test files, conftest.py, and __main__.py
- **Target**: Minimum 80% line coverage, 75% branch coverage

## Coverage Goals by Module

### Core Modules (Target: 90%+)

1. **gmake2cmake/diagnostics.py** - Current: ~95%
   - Diagnostic dataclass validation
   - DiagnosticCollector operations
   - Serialization (JSON, console output)
   - Status: COMPLETE

2. **gmake2cmake/config.py** - Current: ~85%
   - Config model validation (TargetMapping, LinkOverride, CustomRuleConfig)
   - YAML parsing and model instantiation
   - Flag mapping and ignore path handling
   - Status: COMPLETE

3. **gmake2cmake/ir/builder.py** - Current: ~80%
   - SourceFile, Target, Project dataclass creation and validation
   - IR building from BuildFacts
   - Dependency attachment and target classification
   - Status: COMPLETE

### Secondary Modules (Target: 75%+)

4. **gmake2cmake/ir/unknowns.py** - Current: ~90%
   - UnknownConstruct creation and validation
   - Factory pattern for ID generation
   - Serialization to dict format
   - Status: COMPLETE

5. **gmake2cmake/cli.py** - Current: ~80%
   - Argument parsing and validation
   - Pipeline execution and error handling
   - Report generation
   - Status: PARTIAL - CLI integration tests needed

6. **gmake2cmake/fs.py** - Current: ~85%
   - FileSystemAdapter interface and LocalFS implementation
   - File I/O operations
   - Status: COMPLETE

### Test Utilities (Target: 70%+)

7. **tests/conftest.py** - Supporting code for test fixtures
   - FakeFS mock implementation
   - Status: COMPLETE

## Coverage Gaps and TODOs

### Integration Testing Gaps

- [ ] **Parser/Evaluator Pipeline**: Need integration tests covering:
  - Complex Makefile parsing with multiple include levels
  - Variable expansion in different contexts
  - Unknown construct detection and categorization
  - Expected: 5-10 tests covering parser→evaluator→IR flow

- [ ] **CMake Emitter**: Coverage for:
  - Full project file generation with multiple targets
  - Custom command emission
  - Link library normalization
  - Expected: 10-15 tests covering emitter output validation

- [ ] **CLI End-to-End**: Coverage for:
  - Full pipeline from source to CMake output
  - Error handling and recovery
  - Report generation correctness
  - Expected: 5-8 tests with sample Makefiles

### Property-Based Testing Opportunities

- [ ] **Config Model**: Test property preservation through parsing
- [ ] **Path Normalization**: Test consistency across platforms
- [ ] **Diagnostics**: Test deduplication and ordering invariants

### Performance Tests (Optional)

- [ ] Large project handling (1000+ targets)
- [ ] Deep include hierarchies (100+ levels)
- [ ] Memory stability under stress

## Running Coverage

### Full Coverage Report
```bash
pytest --cov=gmake2cmake --cov-report=html --cov-report=term-missing
```

### Coverage with Branch Report
```bash
pytest --cov=gmake2cmake --cov-branch --cov-report=term-missing
```

### Quick Coverage Check
```bash
pytest --cov=gmake2cmake --cov-fail-under=80
```

## Standards

- **Merge Requirement**: Minimum 80% line coverage
- **Critical Modules**: 90%+ coverage for diagnostics, config, IR
- **Test Quality**: All tests must be deterministic and isolated
- **Documentation**: Complex test scenarios should include docstrings

## Recent Additions (TASK-0050, TASK-0051)

- Added comprehensive validation tests for all dataclasses
- Added diagnostic code validation tests
- Configured coverage reporting with pytest-cov
- Established baseline metrics and target goals
