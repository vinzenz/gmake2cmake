"""Custom exception hierarchy for gmake2cmake.

Provides domain-specific exceptions with proper context and error messages.
All exceptions inherit from specific base classes for better error handling.
"""

from __future__ import annotations


class GMake2CMakeError(Exception):
    """Base exception for all gmake2cmake errors."""

    pass


# Configuration errors
class ConfigError(GMake2CMakeError):
    """Base class for configuration-related errors."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    pass


class ConfigFileError(ConfigError):
    """Raised when configuration file cannot be read or parsed."""

    pass


# Discovery and parsing errors
class DiscoveryError(GMake2CMakeError):
    """Base class for Makefile discovery errors."""

    pass


class ParseError(GMake2CMakeError):
    """Base class for Makefile parsing errors."""

    pass


class ParseSyntaxError(ParseError):
    """Raised when Makefile has invalid syntax."""

    pass


class IncludeError(DiscoveryError):
    """Raised when a required include file cannot be found."""

    pass


# Evaluation errors
class EvaluationError(GMake2CMakeError):
    """Base class for evaluation-related errors."""

    pass


class VariableExpansionError(EvaluationError):
    """Raised when variable expansion fails."""

    pass


class RuleEvaluationError(EvaluationError):
    """Raised when a rule cannot be evaluated."""

    pass


# IR building errors
class IRError(GMake2CMakeError):
    """Base class for intermediate representation errors."""

    pass


class IRBuildError(IRError):
    """Raised when IR construction fails."""

    pass


# Emission and output errors
class EmissionError(GMake2CMakeError):
    """Base class for CMake emission errors."""

    pass


class EmissionValidationError(EmissionError):
    """Raised when CMake output validation fails."""

    pass


class FileWriteError(EmissionError):
    """Raised when file output fails."""

    pass


# Parallel execution errors
class ParallelError(GMake2CMakeError):
    """Base class for parallel execution errors."""

    pass


class WorkPartitionError(ParallelError):
    """Raised when work partitioning fails."""

    pass


class WorkerError(ParallelError):
    """Raised when a worker process fails."""

    pass


class ErrorContext:
    """Context information for detailed error reporting."""

    def __init__(
        self,
        error_type: str,
        message: str,
        location: str | None = None,
        context: dict | None = None,
    ) -> None:
        """Initialize error context.

        Args:
            error_type: Classification of the error
            message: Human-readable error message
            location: File and line number where error occurred
            context: Additional context data for debugging
        """
        self.error_type = error_type
        self.message = message
        self.location = location
        self.context = context or {}

    def __str__(self) -> str:
        """Format error context as string."""
        parts = [f"{self.error_type}: {self.message}"]
        if self.location:
            parts.append(f"  at {self.location}")
        for key, value in self.context.items():
            parts.append(f"  {key}: {value}")
        return "\n".join(parts)
