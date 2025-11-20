# Testing Guide

Comprehensive guide to testing gmake2cmake, including unit tests, integration tests, and test-driven development practices.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)

## Testing Philosophy

### Test-Driven Development (TDD)

gmake2cmake follows TDD principles:

1. **Write test first** - Define expected behavior before implementation
2. **Make it fail** - Verify test fails without implementation
3. **Implement** - Write minimum code to pass test
4. **Make it pass** - Verify test passes
5. **Refactor** - Improve code while keeping tests green

### Test Pyramid

```
        ┌─────────────┐
        │     E2E     │  Few comprehensive end-to-end tests
        │   (Manual)  │
        └─────────────┘
       ┌───────────────┐
       │  Integration  │  Moderate number of integration tests
       │     Tests     │
       └───────────────┘
      ┌─────────────────┐
      │   Unit Tests    │  Many focused unit tests
      │   (Fast, Many)  │
      └─────────────────┘
```

- **Unit Tests (70%)**: Test individual functions/classes in isolation
- **Integration Tests (25%)**: Test component interactions
- **End-to-End Tests (5%)**: Test complete workflows

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_parser.py
│   ├── test_evaluator.py
│   ├── test_config.py
│   └── test_diagnostics.py
├── integration/             # Integration tests
│   ├── test_conversion.py
│   ├── test_discovery.py
│   └── test_ir_builder.py
├── fixtures/                # Test data
│   ├── makefiles/
│   │   ├── simple/
│   │   │   └── Makefile
│   │   ├── complex/
│   │   │   └── Makefile
│   │   └── invalid/
│   │       └── Makefile
│   └── configs/
│       └── sample.yaml
└── helpers/                 # Test utilities
    ├── __init__.py
    └── assertions.py
```

### Test File Naming

Convention: `test_<module>.py` for testing `<module>.py`

```
gmake2cmake/parser.py       → tests/unit/test_parser.py
gmake2cmake/ir/builder.py   → tests/unit/ir/test_builder.py
```

### Test Class Organization

Group related tests in classes:

```python
class TestParserBasics:
    """Basic parsing functionality."""

    def test_simple_rule(self):
        """Parse simple target rule."""
        ...

    def test_variable_assignment(self):
        """Parse variable assignment."""
        ...


class TestParserEdgeCases:
    """Edge cases and special syntax."""

    def test_multiline_recipe(self):
        """Parse recipe with line continuations."""
        ...

    def test_special_characters(self):
        """Handle special characters in target names."""
        ...


class TestParserErrors:
    """Error handling and recovery."""

    def test_invalid_syntax(self):
        """Report invalid syntax."""
        ...

    def test_missing_separator(self):
        """Handle missing rule separator."""
        ...
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific file
pytest tests/unit/test_parser.py

# Run specific test class
pytest tests/unit/test_parser.py::TestParserBasics

# Run specific test
pytest tests/unit/test_parser.py::TestParserBasics::test_simple_rule

# Run tests matching pattern
pytest -k "parser"
```

### Verbose Output

```bash
# Verbose output
pytest -v

# Very verbose (show all output)
pytest -vv

# Show print statements
pytest -s
```

### Test Selection

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests with specific marker
pytest -m "slow"

# Exclude marked tests
pytest -m "not slow"
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPUs)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

### Debugging Tests

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of each test
pytest --trace

# Show local variables in traceback
pytest -l
```

### Performance Profiling

```bash
# Show slowest tests
pytest --durations=10

# Profile test execution
pytest --profile

# Use pytest-benchmark
pytest --benchmark-only
```

## Writing Tests

### Unit Test Template

```python
"""Tests for <module> module.

Test coverage:
- Normal operation
- Edge cases
- Error handling
- Performance characteristics
"""

import pytest
from pathlib import Path

from gmake2cmake.module import function_to_test, ClassToTest


class TestFunctionName:
    """Test function_to_test function."""

    def test_normal_case(self):
        """Test normal operation."""
        # Arrange
        input_data = "test input"

        # Act
        result = function_to_test(input_data)

        # Assert
        assert result == "expected output"

    def test_edge_case_empty(self):
        """Test with empty input."""
        result = function_to_test("")
        assert result == ""

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError) as exc_info:
            function_to_test(None)

        assert "cannot be None" in str(exc_info.value)


class TestClassName:
    """Test ClassToTest class."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return ClassToTest(param="value")

    def test_initialization(self, instance):
        """Test instance creation."""
        assert instance.param == "value"

    def test_method(self, instance):
        """Test instance method."""
        result = instance.method("input")
        assert result == "output"
```

### Parametrized Tests

Test multiple inputs efficiently:

```python
@pytest.mark.parametrize("input,expected", [
    ("simple", "SIMPLE"),
    ("with spaces", "WITH_SPACES"),
    ("with-dashes", "WITH_DASHES"),
    ("", ""),
])
def test_normalize(input, expected):
    """Test input normalization."""
    assert normalize(input) == expected
```

Multiple parameters:

```python
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_addition(a, b, expected):
    """Test addition operation."""
    assert add(a, b) == expected
```

### Fixtures

Reusable test components:

```python
# conftest.py - Shared fixtures

@pytest.fixture
def sample_makefile(tmp_path):
    """Create sample Makefile."""
    makefile = tmp_path / "Makefile"
    makefile.write_text("""
    CC = gcc
    CFLAGS = -Wall

    app: main.o
    \t$(CC) $(CFLAGS) -o app main.o
    """)
    return makefile


@pytest.fixture
def config():
    """Create sample configuration."""
    return ConfigModel(
        project_name="TestProject",
        cmake_minimum_version="3.15",
        makefiles=["Makefile"]
    )


@pytest.fixture
def diagnostic_collector():
    """Create diagnostic collector."""
    return DiagnosticCollector()
```

Using fixtures:

```python
def test_parse_makefile(sample_makefile):
    """Parse Makefile fixture."""
    result = parse_makefile(sample_makefile)
    assert "CC" in result.variables


def test_with_config(config, diagnostic_collector):
    """Test with multiple fixtures."""
    converter = Converter(config, diagnostic_collector)
    result = converter.convert()
    assert result.success
```

### Fixture Scopes

Control fixture lifecycle:

```python
@pytest.fixture(scope="function")  # Default: new for each test
def temp_file():
    """Create temporary file."""
    ...


@pytest.fixture(scope="class")  # Shared within test class
def shared_config():
    """Create shared configuration."""
    ...


@pytest.fixture(scope="module")  # Shared within module
def database():
    """Create database connection."""
    ...


@pytest.fixture(scope="session")  # Created once per session
def expensive_resource():
    """Create expensive resource."""
    ...
```

### Mocking and Patching

Mock external dependencies:

```python
from unittest.mock import Mock, patch, MagicMock


def test_with_mock():
    """Test with mocked dependency."""
    mock_parser = Mock()
    mock_parser.parse.return_value = {"result": "data"}

    converter = Converter(parser=mock_parser)
    result = converter.convert()

    mock_parser.parse.assert_called_once()
    assert result == {"result": "data"}


@patch('gmake2cmake.fs.Path.exists')
def test_file_not_found(mock_exists):
    """Test file not found handling."""
    mock_exists.return_value = False

    with pytest.raises(FileNotFoundError):
        load_makefile("nonexistent.mk")


@patch('gmake2cmake.subprocess.run')
def test_external_command(mock_run):
    """Test external command execution."""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="output"
    )

    result = run_make_command("clean")
    assert result == "output"
```

### Testing Exceptions

```python
def test_raises_value_error():
    """Test ValueError is raised."""
    with pytest.raises(ValueError):
        function_that_raises("invalid")


def test_exception_message():
    """Test exception message."""
    with pytest.raises(ValueError) as exc_info:
        function_that_raises("invalid")

    assert "invalid input" in str(exc_info.value)


def test_exception_attributes():
    """Test custom exception attributes."""
    with pytest.raises(ConversionError) as exc_info:
        convert_file("bad.mk")

    assert exc_info.value.filename == "bad.mk"
    assert exc_info.value.line_number == 42
```

### Testing Output

```python
def test_stdout(capsys):
    """Test stdout output."""
    print_message("Hello")

    captured = capsys.readouterr()
    assert captured.out == "Hello\n"


def test_stderr(capsys):
    """Test stderr output."""
    print_error("Error message")

    captured = capsys.readouterr()
    assert "Error message" in captured.err


def test_logging(caplog):
    """Test logging output."""
    import logging

    logger = logging.getLogger("gmake2cmake")
    logger.info("Test message")

    assert "Test message" in caplog.text
    assert caplog.records[0].levelname == "INFO"
```

### Testing Files

```python
def test_creates_file(tmp_path):
    """Test file creation."""
    output_file = tmp_path / "output.txt"

    write_output(output_file, "content")

    assert output_file.exists()
    assert output_file.read_text() == "content"


def test_modifies_file(tmp_path):
    """Test file modification."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("original")

    modify_file(input_file)

    assert input_file.read_text() == "modified"
```

## Test Coverage

### Measuring Coverage

```bash
# Run tests with coverage
pytest --cov=gmake2cmake

# Generate HTML report
pytest --cov=gmake2cmake --cov-report=html

# Show missing lines
pytest --cov=gmake2cmake --cov-report=term-missing

# Generate multiple reports
pytest --cov=gmake2cmake \
    --cov-report=html \
    --cov-report=term \
    --cov-report=xml
```

### Coverage Reports

HTML report structure:
```
htmlcov/
├── index.html           # Overview
├── status.json          # Coverage data
└── gmake2cmake_*.html   # Per-file reports
```

View report:
```bash
# Linux/Mac
open htmlcov/index.html

# Windows
start htmlcov/index.html
```

### Coverage Configuration

`.coveragerc`:
```ini
[run]
source = gmake2cmake
omit =
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstract

[html]
directory = htmlcov
```

### Coverage Goals

- **Overall**: 80% minimum
- **Critical paths**: 100% required
- **New code**: 100% required
- **Utilities**: 90% minimum

Check coverage thresholds:
```bash
pytest --cov=gmake2cmake --cov-fail-under=80
```

## Integration Tests

### Testing Complete Workflows

```python
"""Integration tests for end-to-end conversion."""

import pytest
from pathlib import Path
import subprocess

from gmake2cmake import Converter
from gmake2cmake.config import load_config


class TestCompleteConversion:
    """Test complete Makefile to CMake conversion."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create test project."""
        # Create Makefile
        makefile = tmp_path / "Makefile"
        makefile.write_text("""
        CC = gcc
        TARGET = app

        $(TARGET): main.o utils.o
        \t$(CC) -o $(TARGET) main.o utils.o

        %.o: %.c
        \t$(CC) -c $< -o $@
        """)

        # Create source files
        (tmp_path / "main.c").write_text("int main() { return 0; }")
        (tmp_path / "utils.c").write_text("void utils() {}")

        # Create config
        config = tmp_path / "gmake2cmake.yaml"
        config.write_text("""
        project_name: "TestApp"
        makefiles:
          - Makefile
        """)

        return tmp_path

    def test_conversion_produces_cmake(self, project_dir):
        """Test conversion creates CMakeLists.txt."""
        config = load_config(project_dir / "gmake2cmake.yaml")
        converter = Converter(config)

        result = converter.convert()

        assert result.success
        assert (project_dir / "CMakeLists.txt").exists()

    def test_generated_cmake_builds(self, project_dir):
        """Test generated CMakeLists.txt builds successfully."""
        # Convert
        config = load_config(project_dir / "gmake2cmake.yaml")
        converter = Converter(config)
        converter.convert()

        # Build with CMake
        build_dir = project_dir / "build"
        build_dir.mkdir()

        # Configure
        result = subprocess.run(
            ["cmake", ".."],
            cwd=build_dir,
            capture_output=True
        )
        assert result.returncode == 0

        # Build
        result = subprocess.run(
            ["cmake", "--build", "."],
            cwd=build_dir,
            capture_output=True
        )
        assert result.returncode == 0

        # Verify executable exists
        assert (build_dir / "app").exists()
```

### Testing Component Interactions

```python
class TestParserEvaluatorIntegration:
    """Test parser and evaluator working together."""

    def test_variable_expansion_in_rules(self):
        """Test variables expanded in rules."""
        makefile = """
        CC = gcc
        TARGET = app

        $(TARGET): main.o
        \t$(CC) -o $@ $<
        """

        ast = parse_makefile(makefile)
        context = EvaluationContext()
        expanded = evaluate(ast, context)

        rule = expanded.rules[0]
        assert rule.target == "app"
        assert "gcc -o" in rule.recipe[0]
```

## Continuous Integration

### GitHub Actions Configuration

`.github/workflows/test.yml`:
```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest --cov=gmake2cmake --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

      - name: Run linting
        run: |
          black --check gmake2cmake/ tests/
          mypy gmake2cmake/
          pylint gmake2cmake/
```

### Pre-commit Hooks

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

Install hooks:
```bash
pip install pre-commit
pre-commit install
```

### Test Quality Metrics

Track test quality over time:

```bash
# Test count
pytest --collect-only | grep "test session starts"

# Test duration
pytest --durations=0

# Flaky tests
pytest --flaky --max-runs=3

# Mutation testing
pip install mutmut
mutmut run
```

## See Also

- [Contributing Guide](../CONTRIBUTING.md) - Development workflow
- [Architecture Guide](architecture.md) - System design
- [Performance Guide](performance.md) - Optimization techniques
