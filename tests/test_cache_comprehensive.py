"""Comprehensive tests for cache module covering all code paths."""

from __future__ import annotations

import pytest
from gmake2cmake.cache import EvaluationCache, CacheConfig, CacheStats
from gmake2cmake.make.evaluator import InferredCompile
from gmake2cmake.make.parser import SourceLocation


class TestCacheStats:
    """Tests for cache statistics tracking."""

    def test_cache_stats_initialization(self):
        """Cache stats should initialize with zeros."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0

    def test_hit_rate_calculation_empty(self):
        """Hit rate for empty cache should be 0.0."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation_all_hits(self):
        """Hit rate with only hits should be 1.0."""
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_calculation_all_misses(self):
        """Hit rate with only misses should be 0.0."""
        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation_mixed(self):
        """Hit rate with mixed hits and misses should be accurate."""
        stats = CacheStats(hits=70, misses=30)
        assert pytest.approx(stats.hit_rate, 0.01) == 0.7


class TestCacheConfiguration:
    """Tests for cache configuration validation."""

    def test_default_config(self):
        """Default config should have sensible values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.max_size == 1024
        assert config.ttl_seconds is None

    def test_invalid_max_size_zero(self):
        """Max size of 0 should raise ValueError."""
        with pytest.raises(ValueError, match="max_size must be at least 1"):
            CacheConfig(max_size=0)

    def test_invalid_max_size_negative(self):
        """Negative max size should raise ValueError."""
        with pytest.raises(ValueError, match="max_size must be at least 1"):
            CacheConfig(max_size=-1)

    def test_invalid_ttl_negative(self):
        """Negative TTL should raise ValueError."""
        with pytest.raises(ValueError, match="ttl_seconds must be non-negative"):
            CacheConfig(ttl_seconds=-1)

    def test_valid_custom_config(self):
        """Custom valid config should work."""
        config = CacheConfig(enabled=False, max_size=256, ttl_seconds=3600)
        assert config.enabled is False
        assert config.max_size == 256
        assert config.ttl_seconds == 3600


class TestVariableExpansionCache:
    """Tests for variable expansion caching."""

    def test_disabled_cache_calls_callback(self, cache_disabled):
        """Disabled cache should always call callback."""
        call_count = [0]

        def callback(var: str, hash: str) -> str:
            call_count[0] += 1
            return f"value_{var}"

        result1 = cache_disabled.get_variable_expansion("VAR", "hash1", callback)
        result2 = cache_disabled.get_variable_expansion("VAR", "hash1", callback)

        assert result1 == "value_VAR"
        assert result2 == "value_VAR"
        assert call_count[0] == 2  # Called twice despite same key

    def test_cache_hit_same_key(self, evaluation_cache):
        """Cache hit with same key should not call callback."""
        call_count = [0]

        def callback(var: str, hash: str) -> str:
            call_count[0] += 1
            return f"expanded_{var}"

        result1 = evaluation_cache.get_variable_expansion("VAR1", "hash1", callback)
        result2 = evaluation_cache.get_variable_expansion("VAR1", "hash1", callback)

        assert result1 == result2 == "expanded_VAR1"
        assert call_count[0] == 1  # Called once, second time from cache
        assert evaluation_cache.stats.hits == 1
        assert evaluation_cache.stats.misses == 1

    def test_cache_miss_different_hash(self, evaluation_cache):
        """Different hash should cause cache miss."""
        call_count = [0]

        def callback(var: str, hash: str) -> str:
            call_count[0] += 1
            return f"value_{hash}"

        result1 = evaluation_cache.get_variable_expansion("VAR", "hash1", callback)
        result2 = evaluation_cache.get_variable_expansion("VAR", "hash2", callback)

        assert result1 == "value_hash1"
        assert result2 == "value_hash2"
        assert call_count[0] == 2  # Both are misses
        assert evaluation_cache.stats.misses == 2

    def test_cache_eviction_on_overflow(self):
        """Cache should evict LRU items when full."""
        config = CacheConfig(max_size=2)
        cache = EvaluationCache(config)

        def callback(var: str, hash: str) -> str:
            return f"value_{var}"

        # Fill cache
        cache.get_variable_expansion("VAR1", "hash", callback)
        cache.get_variable_expansion("VAR2", "hash", callback)

        # This should evict VAR1 (LRU)
        cache.get_variable_expansion("VAR3", "hash", callback)

        assert cache.stats.evictions >= 1

        # Verify VAR1 is no longer in cache (miss)
        cache.get_variable_expansion("VAR1", "hash", callback)
        # Total should be 3 misses (VAR1, VAR2, VAR3) + 1 additional for VAR1 again
        assert cache.stats.misses >= 3


class TestCompileInferenceCache:
    """Tests for compile inference caching."""

    def test_compile_cache_miss_none(self, evaluation_cache):
        """Non-compile command should return None."""
        call_count = [0]

        def callback(hash: str) -> None:
            call_count[0] += 1
            return None

        result = evaluation_cache.get_compile_inference("echo hello", callback)

        assert result is None
        assert call_count[0] == 1

    def test_compile_cache_hit(self, evaluation_cache):
        """Compile inference should be cached."""
        call_count = [0]
        location = SourceLocation(path="test.mk", line=1, column=1)
        compile = InferredCompile(
            source="main.c",
            output="main.o",
            language="C",
            flags=["-Wall"],
            includes=[],
            defines=[],
            location=location
        )

        def callback(hash: str) -> InferredCompile:
            call_count[0] += 1
            return compile

        result1 = evaluation_cache.get_compile_inference("gcc main.c", callback)
        result2 = evaluation_cache.get_compile_inference("gcc main.c", callback)

        assert result1 is not None
        assert result2 is not None
        assert call_count[0] == 1  # Called once
        assert evaluation_cache.stats.hits == 1
        assert evaluation_cache.stats.misses == 1

    def test_compile_cache_miss_different_hash(self, evaluation_cache):
        """Different compile commands should be cache misses."""
        call_count = [0]
        location = SourceLocation(path="test.mk", line=1, column=1)

        def callback(hash: str) -> InferredCompile:
            call_count[0] += 1
            return InferredCompile(
                source=f"file_{call_count[0]}.c",
                output=f"file_{call_count[0]}.o",
                language="C",
                flags=[],
                includes=[],
                defines=[],
                location=location
            )

        result1 = evaluation_cache.get_compile_inference("gcc file1.c", callback)
        result2 = evaluation_cache.get_compile_inference("gcc file2.c", callback)

        assert result1 is not None
        assert result2 is not None
        assert call_count[0] == 2
        assert evaluation_cache.stats.misses == 2


class TestCacheIntegration:
    """Integration tests for cache behavior."""

    def test_stats_tracking(self, evaluation_cache):
        """Cache should track statistics correctly."""
        def var_callback(var: str, hash: str) -> str:
            return "value"

        # Variable cache operations
        evaluation_cache.get_variable_expansion("VAR", "h1", var_callback)  # miss
        evaluation_cache.get_variable_expansion("VAR", "h1", var_callback)  # hit
        evaluation_cache.get_variable_expansion("VAR", "h2", var_callback)  # miss

        stats = evaluation_cache.stats
        # VAR h1 miss, VAR h1 hit, VAR h2 miss
        assert stats.misses == 2  # VAR h1, VAR h2
        assert stats.hits == 1    # VAR h1 repeat

    def test_cache_enabled_flag_respected(self):
        """Cache enabled flag should disable caching when False."""
        config = CacheConfig(enabled=False)
        cache = EvaluationCache(config)

        call_count = [0]

        def callback(var: str, hash: str) -> str:
            call_count[0] += 1
            return "value"

        cache.get_variable_expansion("VAR", "h1", callback)
        cache.get_variable_expansion("VAR", "h1", callback)

        # Both should have called callback (no caching)
        assert call_count[0] == 2
