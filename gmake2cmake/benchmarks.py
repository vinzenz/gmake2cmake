"""Performance benchmarking framework for gmake2cmake pipeline.

Provides utilities for measuring and comparing performance across
different versions and optimization strategies.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeVar, Any

T = TypeVar("T")


@dataclass
class BenchmarkResult:
    """Result of a single benchmark measurement.

    Attributes:
        name: Name of the benchmark
        elapsed_seconds: Total elapsed time in seconds
        memory_peak_mb: Peak memory usage in megabytes
        iterations: Number of iterations performed
        ops_per_sec: Operations per second (if applicable)
    """

    name: str
    elapsed_seconds: float
    memory_peak_mb: float = 0.0
    iterations: int = 1
    ops_per_sec: float = 0.0

    @property
    def avg_time_ms(self) -> float:
        """Average time per iteration in milliseconds."""
        if self.iterations == 0:
            return 0.0
        return (self.elapsed_seconds / self.iterations) * 1000

    def __str__(self) -> str:
        """Format benchmark result as string."""
        return (
            f"{self.name:40s} | "
            f"{self.elapsed_seconds:8.3f}s | "
            f"{self.avg_time_ms:8.3f}ms | "
            f"{self.memory_peak_mb:8.1f}MB"
        )


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results with statistics.

    Attributes:
        name: Name of the benchmark suite
        results: List of individual benchmark results
        baseline: Optional baseline suite for comparison
    """

    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    baseline: Optional[BenchmarkSuite] = None

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the suite.

        Args:
            result: BenchmarkResult to add
        """
        self.results.append(result)

    def total_time(self) -> float:
        """Get total time across all benchmarks.

        Returns:
            Total elapsed time in seconds
        """
        return sum(r.elapsed_seconds for r in self.results)

    def get_comparison_with_baseline(self, name: str) -> Dict[str, float]:
        """Compare a result with baseline.

        Args:
            name: Name of the benchmark to compare

        Returns:
            Dictionary with improvement metrics
        """
        if not self.baseline:
            return {}

        current = next((r for r in self.results if r.name == name), None)
        baseline = next((r for r in self.baseline.results if r.name == name), None)

        if not current or not baseline:
            return {}

        time_ratio = current.elapsed_seconds / baseline.elapsed_seconds if baseline.elapsed_seconds > 0 else 1.0
        time_improvement = (1 - time_ratio) * 100

        memory_ratio = current.memory_peak_mb / baseline.memory_peak_mb if baseline.memory_peak_mb > 0 else 1.0
        memory_improvement = (1 - memory_ratio) * 100

        return {
            "time_ratio": time_ratio,
            "time_improvement_percent": time_improvement,
            "memory_ratio": memory_ratio,
            "memory_improvement_percent": memory_improvement,
        }

    def print_summary(self) -> str:
        """Print summary of all benchmark results.

        Returns:
            Formatted string with results
        """
        lines = [
            f"\nBenchmark Suite: {self.name}",
            "=" * 90,
            f"{'Benchmark':<40} {'Total (s)':<12} {'Avg (ms)':<12} {'Peak (MB)':<12}",
            "-" * 90,
        ]

        for result in self.results:
            lines.append(str(result))

        lines.append("-" * 90)
        lines.append(f"{'TOTAL':<40} {self.total_time():<12.3f}s")

        if self.baseline:
            lines.append("\n" + "Comparison with Baseline:")
            lines.append("-" * 90)
            for result in self.results:
                comparison = self.get_comparison_with_baseline(result.name)
                if comparison:
                    improvement = comparison.get("time_improvement_percent", 0)
                    sign = "+" if improvement > 0 else ""
                    lines.append(
                        f"{result.name:<40} {sign}{improvement:>6.1f}% "
                        f"({comparison['time_ratio']:.2f}x)"
                    )

        return "\n".join(lines)


class Benchmark:
    """Context manager for benchmarking code blocks.

    Example:
        >>> with Benchmark("operation", track_memory=True) as bench:
        ...     expensive_operation()
        >>> print(bench.result)
    """

    def __init__(
        self,
        name: str,
        track_memory: bool = False,
        iterations: int = 1,
    ) -> None:
        """Initialize benchmark context.

        Args:
            name: Name of the operation being benchmarked
            track_memory: If True, track peak memory usage
            iterations: Number of iterations (for averaging)
        """
        self.name = name
        self.track_memory = track_memory
        self.iterations = iterations
        self.result: Optional[BenchmarkResult] = None
        self._start_time: float = 0.0
        self._start_memory: int = 0
        self._peak_memory: int = 0

    def __enter__(self) -> Benchmark:
        """Enter benchmark context."""
        self._start_time = time.perf_counter()
        if self.track_memory:
            tracemalloc.start()
            self._start_memory, _ = tracemalloc.get_traced_memory()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit benchmark context and record result."""
        elapsed = time.perf_counter() - self._start_time

        memory_peak_mb = 0.0
        if self.track_memory:
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_peak_mb = (peak - self._start_memory) / (1024 * 1024)

        self.result = BenchmarkResult(
            name=self.name,
            elapsed_seconds=elapsed,
            memory_peak_mb=max(0.0, memory_peak_mb),
            iterations=self.iterations,
        )


def benchmark_function(
    func: Callable[..., T],
    *args: Any,
    name: Optional[str] = None,
    iterations: int = 1,
    track_memory: bool = False,
    **kwargs: Any,
) -> tuple[T, BenchmarkResult]:
    """Benchmark a function call.

    Args:
        func: Function to benchmark
        *args: Positional arguments for function
        name: Name for the benchmark (defaults to function name)
        iterations: Number of iterations to run
        track_memory: If True, track peak memory usage
        **kwargs: Keyword arguments for function

    Returns:
        Tuple of (function_result, BenchmarkResult)
    """
    benchmark_name = name or func.__name__

    with Benchmark(benchmark_name, track_memory=track_memory, iterations=iterations) as bench:
        result = None
        for _ in range(iterations):
            result = func(*args, **kwargs)

    return result, bench.result  # type: ignore


def profile_function(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Profile a function and print results.

    Args:
        func: Function to profile
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    import cProfile
    import pstats
    from io import StringIO

    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()

    # Print statistics
    stats = pstats.Stats(profiler, stream=StringIO())
    stats.sort_stats("cumulative")
    stats.print_stats(10)  # Top 10 functions

    return result


# Performance targets
PERFORMANCE_TARGETS = {
    "parse_makefile": {
        "time_ms": 10,
        "description": "Parse single Makefile",
    },
    "evaluate_variables": {
        "time_ms": 1,
        "description": "Evaluate variable expansion",
    },
    "discover_makefiles": {
        "time_ms": 100,
        "description": "Discover Makefiles in project",
    },
    "build_project": {
        "time_ms": 500,
        "description": "Build complete IR",
    },
    "emit_cmake": {
        "time_ms": 100,
        "description": "Emit CMakeLists.txt",
    },
}
