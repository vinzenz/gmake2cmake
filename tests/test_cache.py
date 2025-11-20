"""Tests for evaluation cache functionality."""

import pytest

from gmake2cmake.cache import (
    CacheConfig,
    CacheStats,
    EvaluationCache,
    make_cache_default,
    make_cache_disabled,
)


class TestCacheConfig:
    """Tests for cache configuration."""

    def test_default_config(self):
        """Test default cache configuration."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.max_size == 1024
        assert config.ttl_seconds is None

    def test_custom_config(self):
        """Test custom cache configuration."""
        config = CacheConfig(enabled=False, max_size=512, ttl_seconds=60.0)
        assert config.enabled is False
        assert config.max_size == 512
        assert config.ttl_seconds == 60.0

    def test_invalid_max_size(self):
        """Test invalid max size raises error."""
        with pytest.raises(ValueError):
            CacheConfig(max_size=0)
        with pytest.raises(ValueError):
            CacheConfig(max_size=-1)

    def test_invalid_ttl(self):
        """Test invalid TTL raises error."""
        with pytest.raises(ValueError):
            CacheConfig(ttl_seconds=-1)


class TestCacheStats:
    """Tests for cache statistics."""

    def test_initial_stats(self):
        """Test initial cache statistics."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=3, misses=1)
        assert stats.hit_rate == 0.75

    def test_hit_rate_all_hits(self):
        """Test hit rate when all lookups hit."""
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        """Test hit rate when all lookups miss."""
        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0


class TestEvaluationCache:
    """Tests for EvaluationCache."""

    def test_disabled_cache(self):
        """Test cache returns fresh values when disabled."""
        config = CacheConfig(enabled=False)
        cache = EvaluationCache(config)

        call_count = 0

        def callback(var_name, env_hash):
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"

        result1 = cache.get_variable_expansion("VAR", "hash1", callback)
        result2 = cache.get_variable_expansion("VAR", "hash1", callback)

        assert result1 == "value_1"
        assert result2 == "value_2"
        assert call_count == 2
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0

    def test_enabled_cache_hits(self):
        """Test cache returns cached values when hit."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        call_count = 0

        def callback(var_name, env_hash):
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"

        result1 = cache.get_variable_expansion("VAR", "hash1", callback)
        result2 = cache.get_variable_expansion("VAR", "hash1", callback)

        assert result1 == "value_1"
        assert result2 == "value_1"
        assert call_count == 1
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_cache_different_vars(self):
        """Test cache distinguishes different variables."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        def callback(var_name, env_hash):
            return f"{var_name}_{env_hash}"

        result1 = cache.get_variable_expansion("VAR1", "hash1", callback)
        result2 = cache.get_variable_expansion("VAR2", "hash1", callback)

        assert result1 == "VAR1_hash1"
        assert result2 == "VAR2_hash1"
        assert cache.stats.hits == 0
        assert cache.stats.misses == 2

    def test_cache_different_env_hashes(self):
        """Test cache distinguishes different environment states."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        def callback(var_name, env_hash):
            return f"{var_name}_{env_hash}"

        result1 = cache.get_variable_expansion("VAR", "hash1", callback)
        result2 = cache.get_variable_expansion("VAR", "hash2", callback)

        assert result1 == "VAR_hash1"
        assert result2 == "VAR_hash2"
        assert cache.stats.hits == 0
        assert cache.stats.misses == 2

    def test_cache_eviction_lru(self):
        """Test LRU eviction when cache is full."""
        config = CacheConfig(enabled=True, max_size=3)
        cache = EvaluationCache(config)

        def callback(var_name, env_hash):
            return var_name

        # Fill cache
        cache.get_variable_expansion("VAR1", "h", callback)
        cache.get_variable_expansion("VAR2", "h", callback)
        cache.get_variable_expansion("VAR3", "h", callback)
        assert cache.stats.misses == 3

        # Access VAR1 to make it recently used
        cache.get_variable_expansion("VAR1", "h", callback)
        assert cache.stats.hits == 1

        # Add new item, should evict VAR2 (oldest unused)
        cache.get_variable_expansion("VAR4", "h", callback)
        assert cache.stats.evictions == 1

        # VAR2 should be evicted
        cache.stats = CacheStats()  # Reset stats
        cache.get_variable_expansion("VAR2", "h", callback)
        assert cache.stats.misses == 1  # VAR2 was evicted

        # VAR1 should still be there
        cache.stats = CacheStats()
        cache.get_variable_expansion("VAR1", "h", callback)
        assert cache.stats.hits == 1

    def test_clear_cache(self):
        """Test clearing cache."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        def callback(var_name, env_hash):
            return "value"

        cache.get_variable_expansion("VAR", "h", callback)
        assert cache.stats.hits + cache.stats.misses > 0

        cache.clear()
        assert len(cache._variable_cache) == 0
        assert len(cache._compile_cache) == 0
        assert len(cache._access_order) == 0

    def test_get_stats(self):
        """Test getting cache statistics."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        def callback(var_name, env_hash):
            return "value"

        cache.get_variable_expansion("VAR", "h", callback)
        cache.get_variable_expansion("VAR", "h", callback)

        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.evictions == 0

    def test_compile_inference_caching(self):
        """Test compile inference caching."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        call_count = 0

        def callback(cmd_hash):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Return a compile result on first call
                from gmake2cmake.make.evaluator import InferredCompile
                from gmake2cmake.make.parser import SourceLocation
                return InferredCompile(
                    source="test.c",
                    output="test.o",
                    language="c",
                    flags=["-O2"],
                    includes=["-I."],
                    defines=["-DDEBUG"],
                    location=SourceLocation(path="Makefile", line=1, column=1),
                )
            return None

        result1 = cache.get_compile_inference("hash1", callback)
        result2 = cache.get_compile_inference("hash1", callback)

        assert result1 is not None
        assert result2 is not None
        assert result1 == result2
        assert call_count == 1
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_compile_inference_none_not_cached(self):
        """Test that None results from compile inference are not cached."""
        config = CacheConfig(enabled=True, max_size=100)
        cache = EvaluationCache(config)

        call_count = 0

        def callback(cmd_hash):
            nonlocal call_count
            call_count += 1
            return None

        result1 = cache.get_compile_inference("hash1", callback)
        result2 = cache.get_compile_inference("hash1", callback)

        assert result1 is None
        assert result2 is None
        # Both calls go to callback since None is not cached
        assert call_count == 2


class TestCacheFactories:
    """Tests for cache factory functions."""

    def test_make_cache_disabled(self):
        """Test making disabled cache."""
        cache = make_cache_disabled()
        assert cache.config.enabled is False

    def test_make_cache_default(self):
        """Test making default cache."""
        cache = make_cache_default()
        assert cache.config.enabled is True
        assert cache.config.max_size == 1024
        assert cache.config.ttl_seconds is None
