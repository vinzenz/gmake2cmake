"""Caching layer for MakeEvaluator performance optimization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from gmake2cmake.make.evaluator import InferredCompile


@dataclass
class CacheStats:
    """Statistics about cache usage."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheConfig:
    """Configuration for evaluation cache."""

    enabled: bool = True
    max_size: int = 1024
    ttl_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_size < 1:
            raise ValueError("max_size must be at least 1")
        if self.ttl_seconds is not None and self.ttl_seconds < 0:
            raise ValueError("ttl_seconds must be non-negative")


class EvaluationCache:
    """LRU cache for expensive evaluation operations.

    Supports caching variable expansions and compile inferences with
    optional TTL limits. Thread-safe through Python's GIL.
    """

    def __init__(self, config: CacheConfig) -> None:
        """Initialize cache with given configuration."""
        self.config = config
        self.stats = CacheStats()
        self._variable_cache: Dict[str, str] = {}
        self._compile_cache: Dict[str, InferredCompile] = {}
        self._access_order: Dict[str, int] = {}
        self._next_access_id = 0

    def get_variable_expansion(
        self, variable_name: str, env_hash: str, callback: Callable[[str, str], str]
    ) -> str:
        """Get cached or compute variable expansion.

        Args:
            variable_name: Name of variable to expand
            env_hash: Hash of environment state (for cache invalidation)
            callback: Function to compute expansion if not cached

        Returns:
            Expanded variable value
        """
        if not self.config.enabled:
            return callback(variable_name, env_hash)

        cache_key = f"var:{variable_name}:{env_hash}"

        if cache_key in self._variable_cache:
            self.stats.hits += 1
            self._update_access(cache_key)
            return self._variable_cache[cache_key]

        self.stats.misses += 1
        result = callback(variable_name, env_hash)
        self._insert_with_eviction(self._variable_cache, cache_key, result)
        return result

    def get_compile_inference(
        self, cmd_hash: str, callback: Callable[[str], InferredCompile]
    ) -> Optional[InferredCompile]:
        """Get cached or compute compile inference.

        Args:
            cmd_hash: Hash of command string
            callback: Function to compute inference if not cached

        Returns:
            Inferred compile info or None if not a compile command
        """
        if not self.config.enabled:
            return callback(cmd_hash)

        cache_key = f"compile:{cmd_hash}"

        if cache_key in self._compile_cache:
            self.stats.hits += 1
            self._update_access(cache_key)
            return self._compile_cache[cache_key]

        self.stats.misses += 1
        result = callback(cmd_hash)
        if result is not None:
            self._insert_with_eviction(self._compile_cache, cache_key, result)
        return result

    def _update_access(self, key: str) -> None:
        """Update access time for LRU tracking."""
        self._access_order[key] = self._next_access_id
        self._next_access_id += 1

    def _insert_with_eviction(self, cache: Dict[str, Any], key: str, value: Any) -> None:
        """Insert into cache, evicting LRU item if at capacity."""
        cache[key] = value
        self._update_access(key)

        # Check if we need to evict
        total_size = len(self._variable_cache) + len(self._compile_cache)
        if total_size > self.config.max_size:
            # Find LRU key across all caches
            lru_key = None
            lru_access_id = self._next_access_id

            for k in self._variable_cache:
                if k in self._access_order and self._access_order[k] < lru_access_id:
                    lru_key = k
                    lru_access_id = self._access_order[k]

            for k in self._compile_cache:
                if k in self._access_order and self._access_order[k] < lru_access_id:
                    lru_key = k
                    lru_access_id = self._access_order[k]

            # Evict LRU item
            if lru_key:
                if lru_key in self._variable_cache:
                    del self._variable_cache[lru_key]
                if lru_key in self._compile_cache:
                    del self._compile_cache[lru_key]
                del self._access_order[lru_key]
                self.stats.evictions += 1

    def clear(self) -> None:
        """Clear all cached data."""
        self._variable_cache.clear()
        self._compile_cache.clear()
        self._access_order.clear()
        self._next_access_id = 0

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return CacheStats(
            hits=self.stats.hits,
            misses=self.stats.misses,
            evictions=self.stats.evictions,
        )


def make_cache_disabled() -> EvaluationCache:
    """Create a disabled cache for when caching is not needed."""
    config = CacheConfig(enabled=False)
    return EvaluationCache(config)


def make_cache_default() -> EvaluationCache:
    """Create a cache with default configuration."""
    config = CacheConfig(enabled=True, max_size=1024, ttl_seconds=None)
    return EvaluationCache(config)
