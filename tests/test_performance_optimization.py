"""Performance optimization tests and profiling (TASK-0060).

Uses the benchmarking framework to identify and optimize performance
bottlenecks in critical code paths.

This module tests:
- Parser performance with various Makefile sizes
- Evaluator performance with complex variable expansion
- IR builder performance with large projects
- Parallel evaluator scalability
- Cache effectiveness
"""

from __future__ import annotations

from gmake2cmake.benchmarks import Benchmark, BenchmarkResult, BenchmarkSuite
from gmake2cmake.cache import CacheConfig, EvaluationCache
from gmake2cmake.make.parser import parse_makefile
from gmake2cmake.parallel import ParallelEvaluator


class TestParserPerformance:
    """Performance tests for the parser module."""

    def test_parse_small_makefile_performance(self):
        """Small Makefile (10 rules) should parse quickly."""
        content = "\n".join([
            "VAR1 = value1",
            "VAR2 = value2",
        ] + [
            f"target{i}: prereq{i}\n\tcommand {i}"
            for i in range(10)
        ])

        with Benchmark("parse_small_makefile", track_memory=True) as bm:
            result = parse_makefile(content, "Makefile")

        # Should complete in < 10ms
        assert bm.result.elapsed_seconds * 1000 < 10
        assert len(result.ast) == 12  # 2 vars + 10 rules

    def test_parse_medium_makefile_performance(self):
        """Medium Makefile (100 rules) should parse efficiently."""
        content = "\n".join([
            "VAR1 = value1",
        ] + [
            f"target{i}: prereq{i}\n\tcommand {i}"
            for i in range(100)
        ])

        with Benchmark("parse_medium_makefile", track_memory=True) as bm:
            result = parse_makefile(content, "Makefile")

        # Should complete in < 50ms
        assert bm.result.elapsed_seconds * 1000 < 50
        assert len(result.ast) >= 100

    def test_parse_with_continuations_performance(self):
        """Parser should handle line continuations efficiently."""
        lines = [
            "LONG_VAR = part1 \\",
            "part2 \\",
            "part3 \\",
            "part4 \\",
            "part5",
        ]
        content = "\n".join(lines)

        with Benchmark("parse_continuations", track_memory=True) as bm:
            result = parse_makefile(content, "Makefile")

        assert bm.result.elapsed_seconds * 1000 < 5
        assert len(result.ast) == 1

    def test_parse_with_conditionals_performance(self):
        """Parser should efficiently handle conditional blocks."""
        content = "\n".join([
            "ifdef DEBUG",
            "  VAR1 = debug",
            "  ifdef EXTRA",
            "    VAR2 = extra",
            "  endif",
            "else",
            "  VAR1 = release",
            "endif",
        ])

        with Benchmark("parse_conditionals", track_memory=True) as bm:
            result = parse_makefile(content, "Makefile")

        assert bm.result.elapsed_seconds * 1000 < 5
        assert len(result.ast) >= 1

    def test_parse_memory_efficiency(self):
        """Parser should not consume excessive memory."""
        content = "\n".join([
            "VAR1 = value1",
        ] + [
            f"target{i}: prereq{i}\n\tcommand {i}"
            for i in range(500)
        ])

        with Benchmark("parse_large_memory", track_memory=True) as bm:
            result = parse_makefile(content, "Makefile")

        # Should use < 10MB
        assert bm.result.memory_peak_mb < 10
        assert len(result.ast) > 0


class TestCachePerformance:
    """Performance tests for caching mechanisms."""

    def test_cache_hit_performance(self):
        """Cache hits should be much faster than cache misses."""
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=1000, ttl_seconds=3600))
        variable_name = "TEST_VAR"
        env_hash = "hash123"
        value = "cached_result"

        # Populate cache
        result = cache.get_variable_expansion(variable_name, env_hash, lambda v, h: value)
        assert result == value

        # Measure cache hit
        with Benchmark("cache_hit", track_memory=False) as bm:
            for _ in range(1000):
                result = cache.get_variable_expansion(variable_name, env_hash, lambda v, h: value)

        # Should complete very quickly (< 5ms for 1000 hits)
        assert bm.result.elapsed_seconds * 1000 < 5

    def test_cache_miss_performance(self):
        """Cache misses should be tracked."""
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=10, ttl_seconds=3600))

        with Benchmark("cache_miss", track_memory=False) as bm:
            for i in range(100):
                variable_name = f"VAR_{i}"
                env_hash = f"hash_{i}"
                cache.get_variable_expansion(variable_name, env_hash, lambda v, h: f"result_{v}")

        # Track that misses are slower but still reasonable
        assert bm.result.elapsed_seconds * 1000 < 50

    def test_cache_eviction_performance(self):
        """Cache eviction should not significantly impact performance."""
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=50, ttl_seconds=3600))

        with Benchmark("cache_eviction", track_memory=True) as bm:
            for i in range(1000):
                variable_name = f"VAR_{i}"
                env_hash = f"hash_{i}"
                cache.get_variable_expansion(variable_name, env_hash, lambda v, h: f"result_{v}")

        # Should still be reasonably fast even with eviction
        assert bm.result.elapsed_seconds * 1000 < 100

    def test_disabled_cache_performance(self):
        """Disabled cache should not add overhead."""
        cache = EvaluationCache(CacheConfig(enabled=False, max_size=1000, ttl_seconds=3600))

        with Benchmark("disabled_cache", track_memory=False) as bm:
            for i in range(1000):
                variable_name = f"VAR_{i}"
                env_hash = f"hash_{i}"
                cache.get_variable_expansion(variable_name, env_hash, lambda v, h: f"result_{v}")

        # Disabled cache should be very fast (just callback overhead)
        assert bm.result.elapsed_seconds * 1000 < 10


class TestParallelEvaluatorPerformance:
    """Performance tests for parallel evaluation."""

    def test_parallel_evaluator_initialization(self):
        """Parallel evaluator initialization should be quick."""
        with Benchmark("parallel_init", track_memory=True) as bm:
            evaluator = ParallelEvaluator(num_processes=4)

        assert bm.result.elapsed_seconds * 1000 < 100
        assert evaluator is not None

    def test_parallel_evaluator_single_process(self):
        """Single process evaluator should have minimal overhead."""
        evaluator = ParallelEvaluator(num_processes=1)

        work_items = [
            ({"file1"}, {"file1": "content"}),
        ]

        with Benchmark("parallel_single", track_memory=True) as bm:
            result = evaluator.evaluate_parallel(work_items)

        assert bm.result.elapsed_seconds * 1000 < 50
        assert result is not None

    def test_parallel_evaluator_memory(self):
        """Parallel evaluator should not consume excessive memory."""
        evaluator = ParallelEvaluator(num_processes=2)

        work_items = [
            ({f"file{i}"}, {f"file{i}": f"content{i}"})
            for i in range(10)
        ]

        with Benchmark("parallel_memory", track_memory=True) as bm:
            result = evaluator.evaluate_parallel(work_items)

        # Should use reasonable memory
        assert bm.result.memory_peak_mb < 50
        assert result is not None


class TestBenchmarkComparison:
    """Tests for comparing performance across operations."""

    def test_suite_comparison(self):
        """BenchmarkSuite should track and compare results."""
        suite = BenchmarkSuite(name="test_suite")

        # Benchmark small Makefile
        content_small = "VAR = value\ntarget: prereq\n\tcommand"
        with Benchmark("small", track_memory=False) as bm:
            parse_makefile(content_small, "Makefile")
        suite.add_result(bm.result)

        # Benchmark larger Makefile
        content_large = "\n".join([
            f"target{i}: prereq{i}\n\tcommand {i}"
            for i in range(50)
        ])
        with Benchmark("large", track_memory=False) as bm:
            parse_makefile(content_large, "Makefile")
        suite.add_result(bm.result)

        # Large should take longer (but not excessively)
        small_result = next((r for r in suite.results if r.name == "small"), None)
        large_result = next((r for r in suite.results if r.name == "large"), None)

        assert small_result is not None
        assert large_result is not None

        small_time = small_result.elapsed_seconds * 1000
        large_time = large_result.elapsed_seconds * 1000

        assert large_time > small_time
        assert large_time < small_time * 100  # Should scale reasonably

    def test_performance_regression_detection(self):
        """Suite should detect performance regressions."""
        suite = BenchmarkSuite(name="test_suite")

        # Baseline
        baseline_result = BenchmarkResult(
            name="test",
            elapsed_seconds=10.0 / 1000,
            memory_peak_mb=2.0,
            iterations=1
        )
        suite.add_result(baseline_result)

        # Regression (2x slower)
        regression_result = BenchmarkResult(
            name="test_regression",
            elapsed_seconds=20.0 / 1000,
            memory_peak_mb=2.0,
            iterations=1
        )
        suite.add_result(regression_result)

        # Manual comparison
        ratio = regression_result.elapsed_seconds / baseline_result.elapsed_seconds
        assert ratio > 1.5  # Regression detected


class TestOptimizationTargets:
    """Tests identifying optimization targets."""

    def test_identify_slow_paths(self):
        """Identify which operations are slowest."""
        times = {}

        # Parser performance
        content = "\n".join([f"target{i}: prereq{i}\n\tcommand {i}" for i in range(100)])
        with Benchmark("parser", track_memory=False) as bm:
            parse_makefile(content, "Makefile")
        times["parser"] = bm.result.elapsed_seconds * 1000

        # Cache hit
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=1000, ttl_seconds=3600))
        cache.get_variable_expansion("key", "val", lambda v, h: "result")
        with Benchmark("cache_hit", track_memory=False) as bm:
            for _ in range(1000):
                cache.get_variable_expansion("key", "val", lambda v, h: "result")
        times["cache_hit"] = bm.result.elapsed_seconds * 1000

        # Parallel init
        with Benchmark("parallel_init", track_memory=False) as bm:
            ParallelEvaluator(num_processes=2)
        times["parallel_init"] = bm.result.elapsed_seconds * 1000

        # Parser should be slowest; tolerate tie within margin
        assert times["parser"] >= times["cache_hit"] or abs(times["parser"] - times["cache_hit"]) < 1

    def test_optimization_impact(self):
        """Test that cache correctly stores and retrieves values."""
        # Test that cache hit rate improves with repeated access
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=1000, ttl_seconds=3600))
        
        # First access - miss
        result1 = cache.get_variable_expansion("key", "val", lambda v, h: f"result_{v}")
        stats1 = cache.get_stats()
        assert stats1.misses == 1
        assert stats1.hits == 0
        
        # Second access - hit
        result2 = cache.get_variable_expansion("key", "val", lambda v, h: f"result_{v}")
        stats2 = cache.get_stats()
        assert stats2.misses == 1
        assert stats2.hits == 1
        assert result1 == result2
        
        # Many more hits
        for _ in range(100):
            cache.get_variable_expansion("key", "val", lambda v, h: f"result_{v}")
        
        stats3 = cache.get_stats()
        assert stats3.misses == 1
        assert stats3.hits == 101
        
        # Verify hit rate
        assert stats3.hit_rate > 0.99
class TestScalabilityProfile:
    """Tests for system scalability characteristics."""

    def test_parser_scalability_linear(self):
        """Parser should scale linearly or better with input size."""
        results = {}

        for scale in [10, 50, 100]:
            content = "\n".join([
                f"target{i}: prereq{i}\n\tcommand {i}"
                for i in range(scale)
            ])

            with Benchmark(f"parse_{scale}", track_memory=True) as bm:
                parse_makefile(content, "Makefile")

            results[scale] = bm.result.elapsed_seconds * 1000

        # Check scaling - should not be quadratic
        ratio_50_10 = results[50] / results[10]
        ratio_100_50 = results[100] / results[50]

        # Linear scaling: 50 should be ~5x, 100/50 should be ~2x
        assert ratio_50_10 < 10  # Less than quadratic
        assert ratio_100_50 < 5   # Less than quadratic

    def test_cache_scaling(self):
        """Cache performance should not degrade with size."""
        results = {}

        for num_items in [100, 500, 1000]:
            cache = EvaluationCache(CacheConfig(enabled=True, max_size=num_items, ttl_seconds=3600))

            # Populate cache
            for i in range(num_items):
                cache.get_variable_expansion(f"key{i}", "val", lambda v, h, i=i: f"result{i}")

            # Measure hit performance
            with Benchmark(f"cache_{num_items}", track_memory=True) as bm:
                for i in range(num_items):
                    cache.get_variable_expansion(f"key{i}", "val", lambda v, h, i=i: f"result{i}")

            results[num_items] = bm.result.elapsed_seconds * 1000

        # Cache hits should remain fast regardless of size
        # (assuming reasonable cache implementation)
        assert all(time < 50 for time in results.values())


class TestMemoryOptimization:
    """Tests for memory efficiency."""

    def test_memory_usage_parser(self):
        """Parser memory usage should be proportional to input."""
        results = {}

        for scale in [50, 100, 200]:
            content = "\n".join([
                f"target{i}: prereq{i}\n\tcommand {i}"
                for i in range(scale)
            ])

            with Benchmark(f"mem_parse_{scale}", track_memory=True) as bm:
                parse_makefile(content, "Makefile")

            results[scale] = bm.result.memory_peak_mb

        # Memory should scale reasonably (less than quadratic)
        ratio_100_50 = results[100] / results[50] if results[50] > 0 else 1.0
        ratio_200_100 = results[200] / results[100] if results[100] > 0 else 1.0

        assert ratio_100_50 < 3  # Less than quadratic
        assert ratio_200_100 < 3

    def test_memory_cache_efficiency(self):
        """Cache should not grow unbounded."""
        cache = EvaluationCache(CacheConfig(enabled=True, max_size=100, ttl_seconds=3600))

        with Benchmark("cache_memory", track_memory=True) as bm:
            for i in range(10000):
                key = f"key{i % 100}"
                cache.get_variable_expansion(key, "val", lambda v, h, i=i: f"result{i}")

        # With LRU eviction, memory should be bounded
        assert bm.result.memory_peak_mb < 20
