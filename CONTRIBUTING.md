# Contributing to gmake2cmake

Thank you for your interest in contributing to gmake2cmake! This guide will help you get started with development, testing, and submitting contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- GNU Make (for testing conversions)
- CMake 3.15 or higher (for testing generated files)

### Initial Setup

1. **Fork the repository**

   Visit https://github.com/your-org/gmake2cmake and click "Fork"

2. **Clone your fork**

   ```bash
   git clone https://github.com/YOUR_USERNAME/gmake2cmake.git
   cd gmake2cmake
   ```

3. **Add upstream remote**

   ```bash
   git remote add upstream https://github.com/your-org/gmake2cmake.git
   ```

4. **Run setup script**

   ```bash
   ./scripts/setup.sh
   ```

   This will:
   - Create virtual environment
   - Install dependencies
   - Install development tools
   - Set up pre-commit hooks

5. **Verify installation**

   ```bash
   # Activate virtual environment
   source venv/bin/activate

   # Run tests
   pytest

   # Check code style
   black --check .
   mypy gmake2cmake/
   ```

## Development Environment

### Project Structure

```
gmake2cmake/
├── gmake2cmake/           # Main package
│   ├── __init__.py
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration management
│   ├── make/             # Makefile processing
│   │   ├── parser.py     # Makefile parser
│   │   ├── evaluator.py  # Variable evaluator
│   │   └── discovery.py  # File discovery
│   ├── ir/               # Intermediate representation
│   │   ├── builder.py    # IR construction
│   │   ├── patterns.py   # Pattern recognition
│   │   └── cycles.py     # Cycle detection
│   ├── cmake/            # CMake generation
│   │   └── emitter.py    # CMake emitter
│   └── diagnostics.py    # Diagnostic system
├── tests/                # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test data
├── docs/                 # Documentation
├── scripts/             # Development scripts
└── examples/            # Example projects
```

### Virtual Environment

Always work in a virtual environment:

```bash
# Create environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Development Tools

We use these tools for code quality:

- **black**: Code formatting
- **mypy**: Type checking
- **pylint**: Linting
- **pytest**: Testing
- **coverage**: Code coverage
- **pre-commit**: Git hooks

Install all tools:
```bash
pip install -e ".[dev]"
pre-commit install
```

## Development Workflow

### Creating a Feature Branch

1. **Sync with upstream**

   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   ```

2. **Create feature branch**

   ```bash
   git checkout -b feature/TASK-0001-description
   ```

   Branch naming convention:
   - `feature/TASK-XXXX-description` - New features
   - `bugfix/TASK-XXXX-description` - Bug fixes
   - `docs/TASK-XXXX-description` - Documentation
   - `refactor/TASK-XXXX-description` - Refactoring

### Test-Driven Development (TDD)

We follow TDD practices:

1. **Write failing test first**

   ```python
   # tests/test_new_feature.py
   def test_new_feature():
       """Test that new feature works correctly."""
       result = new_feature("input")
       assert result == "expected"
   ```

2. **Run test to confirm it fails**

   ```bash
   pytest tests/test_new_feature.py -v
   ```

3. **Implement minimum code to pass**

   ```python
   # gmake2cmake/module.py
   def new_feature(input_data):
       """Implement new feature."""
       return "expected"  # Minimal implementation
   ```

4. **Run test to confirm it passes**

   ```bash
   pytest tests/test_new_feature.py -v
   ```

5. **Refactor and improve**

   Improve implementation while keeping tests passing

6. **Add more tests**

   Test edge cases, error conditions, etc.

### Making Changes

1. **Write code**

   - Follow [Code Style](#code-style) guidelines
   - Add type hints
   - Write docstrings
   - Add tests

2. **Run tests**

   ```bash
   # Run all tests
   pytest

   # Run specific test file
   pytest tests/test_parser.py

   # Run with coverage
   pytest --cov=gmake2cmake --cov-report=html
   ```

3. **Check code style**

   ```bash
   # Format code
   black gmake2cmake/ tests/

   # Check types
   mypy gmake2cmake/

   # Run linter
   pylint gmake2cmake/
   ```

4. **Update documentation**

   If you changed:
   - Public API → Update docstrings
   - Behavior → Update docs/
   - Configuration → Update docs/configuration.md

### Committing Changes

1. **Stage changes**

   ```bash
   git add file1.py file2.py
   ```

2. **Write commit message**

   Follow this format:

   ```
   Short summary (50 chars or less)

   Detailed explanation of what changed and why. Wrap at 72 characters.

   - Bullet points for multiple changes
   - Reference issues: Fixes #123
   - Reference tasks: Implements TASK-0001

   Technical details:
   - Implementation approach
   - Trade-offs made
   - Future considerations
   ```

   Example:

   ```
   Add support for wildcard includes in Makefiles

   Implement wildcard expansion for include directives like
   "include *.mk". This allows Makefiles that use wildcard
   includes to be processed correctly.

   - Add glob expansion in discovery.py
   - Handle multiple matching files
   - Preserve include order
   - Add tests for wildcard patterns

   Fixes #42
   Implements TASK-0023
   ```

3. **Commit**

   ```bash
   git commit
   ```

   Pre-commit hooks will run automatically:
   - Code formatting check
   - Type checking
   - Linting
   - Test execution

   Fix any issues before the commit completes.

## Code Style

### Python Style

We follow PEP 8 with these specifics:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Imports**: Grouped (stdlib, third-party, local)

Example:
```python
"""Module docstring.

Detailed description of module purpose and contents.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from external_library import ExternalClass

from gmake2cmake.config import ConfigModel
from gmake2cmake.types import TargetType


def function_name(param1: str, param2: int) -> Optional[str]:
    """Brief description of function.

    Longer description explaining behavior, side effects,
    and important details.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value, or None if condition

    Raises:
        ValueError: When param2 is negative
        TypeError: When param1 is not a string

    Example:
        >>> function_name("test", 42)
        'test_42'
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")

    result = f"{param1}_{param2}"
    return result if result else None
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Dict, List, Optional, Union

def process_targets(
    targets: Dict[str, Target],
    options: Optional[EmitOptions] = None
) -> List[str]:
    """Process targets with optional configuration."""
    ...
```

For complex types, define type aliases:

```python
from typing import Dict, NewType

TargetName = NewType("TargetName", str)
TargetMap = Dict[TargetName, Target]

def build_targets(targets: TargetMap) -> None:
    """Build all targets in map."""
    ...
```

### Docstrings

Use Google style docstrings:

```python
def complex_function(
    arg1: str,
    arg2: int,
    arg3: Optional[List[str]] = None
) -> Dict[str, int]:
    """Brief description (one line).

    Detailed description explaining what the function does,
    how it works, and any important details.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        arg3: Optional description. Defaults to None.

    Returns:
        Dictionary mapping strings to integers. Each key is
        derived from arg1, values from arg2.

    Raises:
        ValueError: If arg2 is negative
        KeyError: If arg1 not found in lookup

    Example:
        >>> complex_function("test", 5)
        {'test_0': 0, 'test_1': 1, ..., 'test_4': 4}

    Note:
        This function has O(n) complexity where n is arg2.

    See Also:
        simple_function: Simpler version without arg3
    """
```

### Code Organization

Organize code logically:

```python
# 1. Imports (grouped)
import stdlib
from typing import ...

import third_party

from local import ...


# 2. Constants
DEFAULT_VALUE = 42
MAX_RETRIES = 3


# 3. Type definitions
class CustomType(Enum):
    ...


# 4. Helper functions
def _internal_helper():
    """Private helper (starts with _)."""
    ...


# 5. Public functions
def public_function():
    """Public API."""
    ...


# 6. Classes
class MainClass:
    """Main functionality."""
    ...
```

## Testing

### Test Structure

Tests mirror source structure:

```
gmake2cmake/parser.py    →  tests/test_parser.py
gmake2cmake/ir/builder.py →  tests/ir/test_builder.py
```

### Writing Tests

Use pytest conventions:

```python
"""Tests for parser module.

Test coverage:
- Basic parsing
- Error handling
- Edge cases
"""

import pytest
from pathlib import Path

from gmake2cmake.make.parser import parse_makefile, ParseError


class TestBasicParsing:
    """Test basic Makefile parsing."""

    def test_simple_rule(self):
        """Parse simple target rule."""
        makefile = """
        target: dependency
        \tcommand
        """
        result = parse_makefile(makefile)

        assert len(result.rules) == 1
        assert result.rules[0].target == "target"
        assert result.rules[0].dependencies == ["dependency"]

    def test_variable_assignment(self):
        """Parse variable assignment."""
        makefile = "VAR = value"
        result = parse_makefile(makefile)

        assert "VAR" in result.variables
        assert result.variables["VAR"] == "value"


class TestErrorHandling:
    """Test error handling in parser."""

    def test_invalid_syntax(self):
        """Raise ParseError on invalid syntax."""
        makefile = "invalid :: syntax"

        with pytest.raises(ParseError) as exc_info:
            parse_makefile(makefile)

        assert "unexpected token" in str(exc_info.value).lower()

    def test_missing_recipe(self):
        """Handle missing recipe gracefully."""
        makefile = "target: dependency"
        result = parse_makefile(makefile)

        assert len(result.rules) == 1
        assert result.rules[0].recipe == []


@pytest.fixture
def sample_makefile(tmp_path):
    """Create sample Makefile for testing."""
    makefile = tmp_path / "Makefile"
    makefile.write_text("""
    CC = gcc
    TARGET = app

    $(TARGET): main.o
    \t$(CC) -o $(TARGET) main.o
    """)
    return makefile


def test_parse_file(sample_makefile):
    """Parse Makefile from file."""
    result = parse_makefile(sample_makefile)

    assert result.variables["CC"] == "gcc"
    assert result.variables["TARGET"] == "app"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_parser.py

# Run specific test
pytest tests/test_parser.py::TestBasicParsing::test_simple_rule

# Run with coverage
pytest --cov=gmake2cmake --cov-report=html

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run tests matching pattern
pytest -k "parse"
```

### Coverage Requirements

- **Minimum coverage**: 80% overall
- **New code**: 100% coverage required
- **Critical paths**: 100% coverage required

Check coverage:
```bash
pytest --cov=gmake2cmake --cov-report=term-missing
```

## Documentation

### Code Documentation

Every public function/class needs:

1. **Docstring** with:
   - Brief description
   - Parameter descriptions
   - Return value description
   - Example usage
   - Related functions

2. **Type hints** for all parameters and returns

3. **Inline comments** for complex logic

### User Documentation

Update user docs when changing:

- Configuration options → `docs/configuration.md`
- CLI interface → `docs/cli.md`
- Behavior → Relevant doc file

### Building Documentation

```bash
# Install doc dependencies
pip install -e ".[docs]"

# Build HTML docs
cd docs
make html

# View docs
open _build/html/index.html
```

## Submitting Changes

### Before Submitting

Checklist:

- [ ] All tests pass
- [ ] Code coverage > 80%
- [ ] Code formatted with black
- [ ] No type errors (mypy)
- [ ] No linting errors (pylint)
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Commit messages follow format

### Creating Pull Request

1. **Push to your fork**

   ```bash
   git push origin feature/TASK-0001-description
   ```

2. **Create PR on GitHub**

   - Go to https://github.com/your-org/gmake2cmake
   - Click "New Pull Request"
   - Select your branch
   - Fill in PR template

3. **PR Title Format**

   ```
   [TASK-0001] Brief description of change
   ```

4. **PR Description Template**

   ```markdown
   ## Description
   Brief summary of changes and motivation.

   ## Changes Made
   - Specific change 1
   - Specific change 2

   ## Testing
   - How changes were tested
   - New test cases added

   ## Breaking Changes
   - List any breaking changes
   - Migration steps if needed

   ## Checklist
   - [x] Tests pass
   - [x] Documentation updated
   - [x] Changelog updated
   - [x] No linting errors

   ## Related Issues
   Fixes #42
   Implements TASK-0001
   ```

### CI/CD Checks

Pull requests automatically run:

- **Tests**: All test suites
- **Coverage**: Coverage must not decrease
- **Linting**: black, mypy, pylint
- **Documentation**: Doc build must succeed

All checks must pass before merge.

## Review Process

### What Reviewers Look For

- **Correctness**: Does it work as intended?
- **Tests**: Adequate test coverage?
- **Code quality**: Follows style guidelines?
- **Documentation**: Properly documented?
- **Performance**: Any performance concerns?
- **Security**: Any security implications?

### Responding to Feedback

- Be open to suggestions
- Ask questions if unclear
- Make requested changes promptly
- Update PR when ready for re-review

### Merging

Once approved:

- Maintainer will merge (or you if you have permission)
- Squash commits if many small commits
- Use merge commit for significant features
- Delete branch after merge

## Getting Help

### Resources

- **Documentation**: https://gmake2cmake.readthedocs.io
- **Discussions**: https://github.com/your-org/gmake2cmake/discussions
- **Issues**: https://github.com/your-org/gmake2cmake/issues

### Communication Channels

- **GitHub Discussions**: General questions
- **GitHub Issues**: Bug reports, feature requests
- **Email**: maintainers@gmake2cmake.example.com

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Thank You!

Your contributions make gmake2cmake better for everyone. Thank you for your time and effort!
