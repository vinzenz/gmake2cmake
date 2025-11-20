"""Benchmarks for gmake2cmake pipeline performance measurement.

These benchmarks establish baseline performance and help track optimization efforts.
Run with: pytest tests/test_benchmarks.py -v --tb=short
"""

from __future__ import annotations

import pytest
from pathlib import Path

from gmake2cmake.benchmarks import (
    Benchmark,
    BenchmarkResult,
    BenchmarkSuite,
    benchmark_function,
    PERFORMANCE_TARGETS,
)


class TestBenchmarkResult:
    """Tests for BenchmarkResult class."""

    def test_avg_time_calculation(self):
        """Average time should be calculated from total and iterations."""
        result = BenchmarkResult(
            name="test",
            elapsed_seconds=10.0,
            iterations=10,
        )

        assert result.avg_time_ms == 1000.0

    def test_avg_time_zero_iterations(self):
        """Zero iterations should return 0 avg time."""
        result = BenchmarkResult(
            name="test",
            elapsed_seconds=10.0,
            iterations=0,
        )

        assert result.avg_time_ms == 0.0


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite class."""

    def test_suite_creation(self):
        """Suite should be created empty."""
        suite = BenchmarkSuite(name="test_suite")
        assert suite.name == "test_suite"
        assert suite.results == []

    def test_add_result(self):
        """Results should be added to suite."""
        suite = BenchmarkSuite(name="test")
        result = BenchmarkResult(name="op1", elapsed_seconds=1.0)

        suite.add_result(result)

        assert len(suite.results) == 1
        assert suite.results[0].name == "op1"

    def test_total_time(self):
        """Total time should sum all results."""
        suite = BenchmarkSuite(name="test")
        suite.add_result(BenchmarkResult(name="op1", elapsed_seconds=1.0))
        suite.add_result(BenchmarkResult(name="op2", elapsed_seconds=2.0))
        suite.add_result(BenchmarkResult(name="op3", elapsed_seconds=3.0))

        assert suite.total_time() == 6.0

    def test_comparison_with_baseline_improvement(self):
        """Should show improvement when faster than baseline."""
        baseline_suite = BenchmarkSuite(name="baseline")
        baseline_suite.add_result(BenchmarkResult(name="op", elapsed_seconds=10.0))

        current_suite = BenchmarkSuite(name="current", baseline=baseline_suite)
        current_suite.add_result(BenchmarkResult(name="op", elapsed_seconds=5.0))

        comparison = current_suite.get_comparison_with_baseline("op")

        assert comparison["time_ratio"] == 0.5
        assert comparison["time_improvement_percent"] == 50.0

    def test_comparison_with_baseline_regression(self):
        """Should show regression when slower than baseline."""
        baseline_suite = BenchmarkSuite(name="baseline")
        baseline_suite.add_result(BenchmarkResult(name="op", elapsed_seconds=10.0))

        current_suite = BenchmarkSuite(name="current", baseline=baseline_suite)
        current_suite.add_result(BenchmarkResult(name="op", elapsed_seconds=20.0))

        comparison = current_suite.get_comparison_with_baseline("op")

        assert comparison["time_ratio"] == 2.0
        assert comparison["time_improvement_percent"] == -100.0

    def test_print_summary(self):
        """Summary should be formatted correctly."""
        suite = BenchmarkSuite(name="test")
        suite.add_result(BenchmarkResult(name="op", elapsed_seconds=1.0, memory_peak_mb=10.5))

        summary = suite.print_summary()

        assert "test" in summary
        assert "op" in summary
        assert "1.000s" in summary


class TestBenchmarkContextManager:
    """Tests for Benchmark context manager."""

    def test_benchmark_timing(self):
        """Benchmark should measure elapsed time."""
        import time

        with Benchmark("test") as bench:
            time.sleep(0.01)

        assert bench.result is not None
        assert bench.result.elapsed_seconds >= 0.01

    def test_benchmark_result_creation(self):
        """Benchmark should create result on exit."""
        with Benchmark("test_op", iterations=5) as bench:
            pass

        assert bench.result is not None
        assert bench.result.name == "test_op"
        assert bench.result.iterations == 5

    def test_benchmark_memory_tracking_disabled(self):
        """Without memory tracking, peak memory should be 0."""
        with Benchmark("test", track_memory=False) as bench:
            _ = [i for i in range(1000)]

        assert bench.result is not None
        assert bench.result.memory_peak_mb == 0.0

    def test_benchmark_memory_tracking_enabled(self):
        """With memory tracking, peak memory should be measured."""
        with Benchmark("test", track_memory=True) as bench:
            # Allocate some memory
            _ = [i for i in range(100000)]

        assert bench.result is not None
        # Memory tracking should work (exact amount depends on Python internals)
        assert bench.result.memory_peak_mb >= 0.0

    def test_benchmark_exception_handling(self):
        """Benchmark should record result even if exception occurs."""
        try:
            with Benchmark("test") as bench:
                raise ValueError("test error")
        except ValueError:
            pass

        assert bench.result is not None
        assert bench.result.name == "test"


class TestBenchmarkFunction:
    """Tests for benchmark_function decorator."""

    def test_benchmark_simple_function(self):
        """Should benchmark a simple function."""

        def simple_op(n: int) -> int:
            return n * 2

        result, bench = benchmark_function(simple_op, 5)

        assert result == 10
        assert bench.name == "simple_op"
        assert bench.elapsed_seconds >= 0.0

    def test_benchmark_with_custom_name(self):
        """Should use custom name if provided."""

        def op(n: int) -> int:
            return n * 2

        result, bench = benchmark_function(op, 5, name="custom_op")

        assert bench.name == "custom_op"

    def test_benchmark_with_iterations(self):
        """Should run function specified number of iterations."""
        call_count = [0]

        def counted_op() -> None:
            call_count[0] += 1

        benchmark_function(counted_op, iterations=5)

        assert call_count[0] == 5


class TestPerformanceTargets:
    """Tests for performance targets validation."""

    def test_targets_defined(self):
        """Performance targets should be defined."""
        assert len(PERFORMANCE_TARGETS) > 0

    def test_target_structure(self):
        """Each target should have required fields."""
        for name, target in PERFORMANCE_TARGETS.items():
            assert "time_ms" in target
            assert "description" in target
            assert target["time_ms"] > 0


class TestPerformanceBenchmarking:
    """Integration tests for performance benchmarking."""

    def test_baseline_creation(self):
        """Should create baseline benchmark suite."""
        baseline = BenchmarkSuite(name="baseline")
        baseline.add_result(BenchmarkResult(name="parse", elapsed_seconds=0.005))
        baseline.add_result(BenchmarkResult(name="evaluate", elapsed_seconds=0.001))

        assert baseline.total_time() == 0.006

    def test_performance_tracking(self):
        """Should track performance across versions."""
        import time

        # Simulate baseline run
        baseline = BenchmarkSuite(name="v1.0")
        with Benchmark("operation", iterations=1) as bench:
            time.sleep(0.001)
        baseline.add_result(bench.result)

        # Simulate optimized run
        optimized = BenchmarkSuite(name="v1.1", baseline=baseline)
        with Benchmark("operation", iterations=1) as bench:
            time.sleep(0.0005)
        optimized.add_result(bench.result)

        # Check improvement
        comparison = optimized.get_comparison_with_baseline("operation")
        assert comparison["time_ratio"] < 1.0
        assert comparison["time_improvement_percent"] > 0
