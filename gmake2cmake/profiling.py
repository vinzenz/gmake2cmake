"""Lightweight profiling utilities for gmake2cmake pipeline.

This module provides timing decorators and metrics collection
for analyzing pipeline performance.
"""

from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class ProfilingMetrics:
    """Accumulated profiling metrics.

    Attributes:
        stage_timings: Mapping of stage names to elapsed times (seconds)
        stage_counts: Mapping of stage names to invocation counts
        enabled: Whether profiling is currently enabled
    """

    stage_timings: Dict[str, float] = field(default_factory=dict)
    stage_counts: Dict[str, int] = field(default_factory=dict)
    enabled: bool = False

    def add_timing(self, stage: str, elapsed: float) -> None:
        """Record timing for a stage.

        Args:
            stage: Stage name
            elapsed: Elapsed time in seconds

        Returns:
            None
        """
        if not self.enabled:
            return
        self.stage_timings[stage] = self.stage_timings.get(stage, 0.0) + elapsed
        self.stage_counts[stage] = self.stage_counts.get(stage, 0) + 1

    def get_summary(self) -> str:
        """Get human-readable summary of metrics.

        Returns:
            Formatted string with timing summary
        """
        if not self.stage_timings:
            return "No profiling data collected."

        lines = ["Performance Summary:"]
        total_time = sum(self.stage_timings.values())
        for stage in sorted(self.stage_timings.keys()):
            elapsed = self.stage_timings[stage]
            count = self.stage_counts[stage]
            avg = elapsed / count if count else 0.0
            percent = (elapsed / total_time * 100) if total_time else 0.0
            lines.append(
                f"  {stage}: {elapsed:.3f}s ({count}x, {avg:.3f}s avg, {percent:.1f}%)"
            )
        lines.append(f"Total: {total_time:.3f}s")
        return "\n".join(lines)


# Global metrics instance
_metrics = ProfilingMetrics()


def enable_profiling() -> None:
    """Enable global profiling collection.

    Returns:
        None
    """
    _metrics.enabled = True
    logging.getLogger("gmake2cmake.profiling").info("Profiling enabled")


def disable_profiling() -> None:
    """Disable global profiling collection.

    Returns:
        None
    """
    _metrics.enabled = False


def is_profiling_enabled() -> bool:
    """Check if profiling is currently enabled.

    Returns:
        True if profiling is enabled, False otherwise
    """
    return _metrics.enabled


def get_metrics() -> ProfilingMetrics:
    """Get the global profiling metrics instance.

    Returns:
        Current ProfilingMetrics instance
    """
    return _metrics


def reset_metrics() -> None:
    """Reset all profiling metrics.

    Returns:
        None
    """
    _metrics.stage_timings.clear()
    _metrics.stage_counts.clear()


def profile_stage(stage_name: str) -> Callable[[F], F]:
    """Decorator to profile execution time of a function/stage.

    Args:
        stage_name: Name of the stage to profile

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _metrics.enabled:
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                _metrics.add_timing(stage_name, elapsed)
                logger = logging.getLogger(f"gmake2cmake.profiling.{stage_name}")
                logger.debug(f"{stage_name} took {elapsed:.3f}s")

        return wrapper  # type: ignore

    return decorator


def timed_block(stage_name: str) -> object:
    """Context manager for timing a code block.

    Usage:
        with timed_block("stage_name"):
            # code to profile

    Args:
        stage_name: Name of the stage

    Returns:
        Context manager object
    """

    class TimedBlock:
        def __init__(self, name: str) -> None:
            self.name = name
            self.start_time: Optional[float] = None

        def __enter__(self) -> TimedBlock:
            if _metrics.enabled:
                self.start_time = time.perf_counter()
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            if _metrics.enabled and self.start_time is not None:
                elapsed = time.perf_counter() - self.start_time
                _metrics.add_timing(self.name, elapsed)
                logger = logging.getLogger(f"gmake2cmake.profiling.{self.name}")
                logger.debug(f"{self.name} took {elapsed:.3f}s")

    return TimedBlock(stage_name)
