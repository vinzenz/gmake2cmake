# Performance Optimization Guide

This guide covers performance optimization techniques for gmake2cmake, including profiling, benchmarking, and scaling strategies for large projects.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Profiling](#profiling)
- [Optimization Techniques](#optimization-techniques)
- [Parallel Processing](#parallel-processing)
- [Caching Strategies](#caching-strategies)
- [Memory Management](#memory-management)
- [Benchmarking](#benchmarking)
- [Scalability](#scalability)

## Performance Overview

### Performance Characteristics

Typical performance for gmake2cmake:

| Project Size | Makefiles | Targets | Time | Memory |
|-------------|-----------|---------|------|--------|
| Small | 1-5 | <50 | <1s | <100MB |
| Medium | 5-20 | 50-200 | 1-5s | 100-500MB |
| Large | 20-100 | 200-1000 | 5-30s | 500MB-2GB |
| Very Large | 100+ | 1000+ | 30s-5m | 2GB+ |

### Bottlenecks

Common performance bottlenecks:

1. **Parsing**: O(n) in file size, can be slow for large Makefiles
2. **Variable Expansion**: O(n*m) for n variables with m expansions
3. **Dependency Analysis**: O(n²) for n targets in worst case
4. **File I/O**: Disk access for many Makefiles
5. **IR Building**: Memory allocation for large ASTs

## Profiling

### Python Profiling

#### Using cProfile

```bash
# Profile gmake2cmake execution
python -m cProfile -o profile.stats -m gmake2cmake --config config.yaml

# Analyze results
python -m pstats profile.stats
>>> sort cumtime
>>> stats 20
```

#### Using line_profiler

```python
# Add @profile decorator to functions
from line_profiler import profile

@profile
def expensive_function():
    """Function to profile."""
    ...
```

```bash
# Install line_profiler
pip install line_profiler

# Run with profiling
kernprof -l -v script.py
```

#### Using memory_profiler

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Track memory usage."""
    ...
```

```bash
# Install memory_profiler
pip install memory_profiler

# Run with memory profiling
python -m memory_profiler script.py
```

### Built-in Profiling

gmake2cmake includes built-in profiling:

```yaml
# gmake2cmake.yaml
performance:
  profiling:
    enabled: true
    output: "profile_report.txt"
    detailed: true
```

```bash
# Enable profiling via CLI
gmake2cmake --profile --profile-output profile.json
```

Profile output:
```json
{
  "total_time": 12.5,
  "stages": {
    "discovery": {"time": 0.5, "percent": 4.0},
    "parsing": {"time": 3.2, "percent": 25.6},
    "evaluation": {"time": 2.8, "percent": 22.4},
    "ir_building": {"time": 4.5, "percent": 36.0},
    "emission": {"time": 1.5, "percent": 12.0}
  },
  "files_processed": 45,
  "targets_created": 234
}
```

### Profiling Specific Components

```python
from gmake2cmake.profiling import profile_section

def convert_project():
    with profile_section("discovery"):
        files = discover_makefiles()

    with profile_section("parsing"):
        asts = [parse(f) for f in files]

    with profile_section("evaluation"):
        expanded = [evaluate(ast) for ast in asts]

    # Results automatically logged
```

## Optimization Techniques

### 1. Parser Optimization

#### Efficient Tokenization

```python
# Before: String concatenation
def tokenize_slow(text):
    tokens = []
    current = ""
    for char in text:
        if char.isspace():
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char  # Inefficient!
    return tokens


# After: Use list and join
def tokenize_fast(text):
    tokens = []
    current = []
    for char in text:
        if char.isspace():
            if current:
                tokens.append(''.join(current))
                current = []
        else:
            current.append(char)
    return tokens
```

#### Lazy Parsing

```python
# Parse only what's needed
class LazyParser:
    """Parse Makefile sections on demand."""

    def __init__(self, text):
        self._text = text
        self._sections = {}

    def get_section(self, name):
        """Parse section only when requested."""
        if name not in self._sections:
            self._sections[name] = self._parse_section(name)
        return self._sections[name]
```

### 2. Variable Expansion Optimization

#### Memoization

```python
from functools import lru_cache

class OptimizedEvaluator:
    """Evaluator with memoization."""

    @lru_cache(maxsize=1000)
    def expand_variable(self, name, context_hash):
        """Cache expansion results."""
        return self._do_expand(name)
```

#### Short-circuit Evaluation

```python
def expand_if_needed(value):
    """Avoid expansion if not needed."""
    # Fast path: no variables to expand
    if '$' not in value:
        return value

    # Slow path: full expansion
    return expand_variables(value)
```

#### Iterative vs Recursive Expansion

```python
# Before: Recursive (deep call stack)
def expand_recursive(var, context):
    if var not in context:
        return var
    value = context[var]
    if has_reference(value):
        return expand_recursive(value, context)
    return value


# After: Iterative (stack efficient)
def expand_iterative(var, context):
    seen = set()
    current = var

    while current in context:
        if current in seen:
            raise RecursionError(f"Circular reference: {var}")
        seen.add(current)

        value = context[current]
        if not has_reference(value):
            return value
        current = value

    return current
```

### 3. Dependency Analysis Optimization

#### Graph Representation

```python
from collections import defaultdict, deque

class DependencyGraph:
    """Efficient dependency graph."""

    def __init__(self):
        self._edges = defaultdict(set)
        self._reverse = defaultdict(set)

    def add_edge(self, from_node, to_node):
        """O(1) edge addition."""
        self._edges[from_node].add(to_node)
        self._reverse[to_node].add(from_node)

    def topological_sort(self):
        """Kahn's algorithm - O(V + E)."""
        in_degree = defaultdict(int)
        for node in self._edges:
            for neighbor in self._edges[node]:
                in_degree[neighbor] += 1

        queue = deque([n for n in self._edges if in_degree[n] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in self._edges[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result
```

#### Cycle Detection

```python
def detect_cycles_tarjan(graph):
    """Tarjan's algorithm - O(V + E)."""
    index = 0
    stack = []
    indices = {}
    lowlinks = {}
    on_stack = set()
    sccs = []

    def strongconnect(node):
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == node:
                    break
            sccs.append(scc)

    for node in graph:
        if node not in indices:
            strongconnect(node)

    return [scc for scc in sccs if len(scc) > 1]
```

## Parallel Processing

### Configuration

```yaml
# gmake2cmake.yaml
performance:
  parallel: true
  max_workers: 4  # Or 'auto' to detect CPU count
  chunk_size: 10  # Files per worker
```

### Parallel Discovery

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def discover_makefiles_parallel(roots, max_workers=4):
    """Discover Makefiles in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(discover_in_directory, root): root
            for root in roots
        }

        results = []
        for future in as_completed(futures):
            results.extend(future.result())

    return results
```

### Parallel Parsing

```python
from multiprocessing import Pool

def parse_makefiles_parallel(files, max_workers=4):
    """Parse multiple Makefiles in parallel."""
    with Pool(max_workers) as pool:
        results = pool.map(parse_makefile, files)
    return results
```

### Parallel IR Building

```python
def build_ir_parallel(asts, max_workers=4):
    """Build IR for independent projects in parallel."""
    # Group independent projects
    groups = partition_independent(asts)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(build_ir_group, group)
            for group in groups
        ]

        for future in as_completed(futures):
            results.extend(future.result())

    return results
```

### Thread Safety

Ensure thread-safe operations:

```python
from threading import Lock

class ThreadSafeDiagnosticCollector:
    """Thread-safe diagnostic collection."""

    def __init__(self):
        self._diagnostics = []
        self._lock = Lock()

    def add(self, diagnostic):
        """Add diagnostic with thread safety."""
        with self._lock:
            self._diagnostics.append(diagnostic)
```

## Caching Strategies

### File-based Caching

```python
import hashlib
import pickle
from pathlib import Path

class FileCache:
    """Cache parsed Makefiles."""

    def __init__(self, cache_dir=".gmake2cmake_cache"):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(exist_ok=True)

    def _cache_key(self, filepath):
        """Generate cache key from file path and mtime."""
        stat = filepath.stat()
        key_data = f"{filepath}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, filepath):
        """Get cached result."""
        key = self._cache_key(filepath)
        cache_file = self._cache_dir / f"{key}.pkl"

        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def set(self, filepath, data):
        """Cache result."""
        key = self._cache_key(filepath)
        cache_file = self._cache_dir / f"{key}.pkl"

        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
```

### In-Memory Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def parse_makefile_cached(filepath, mtime):
    """Cache parsed Makefile in memory."""
    return parse_makefile(filepath)

# Usage
stat = filepath.stat()
result = parse_makefile_cached(filepath, stat.st_mtime)
```

### Cache Invalidation

```python
def invalidate_cache(filepath):
    """Invalidate cache for file."""
    key = cache_key(filepath)
    cache_file = cache_dir / f"{key}.pkl"
    cache_file.unlink(missing_ok=True)

def clean_cache(max_age_days=7):
    """Clean old cache entries."""
    import time
    cutoff = time.time() - (max_age_days * 86400)

    for cache_file in cache_dir.glob("*.pkl"):
        if cache_file.stat().st_mtime < cutoff:
            cache_file.unlink()
```

## Memory Management

### Large File Handling

```python
def process_large_makefile(filepath):
    """Process large Makefile in chunks."""
    chunk_size = 1024 * 1024  # 1MB chunks

    with open(filepath, 'r') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            process_chunk(chunk)
```

### Streaming Processing

```python
def stream_process_makefiles(files):
    """Process Makefiles as stream to reduce memory."""
    for filepath in files:
        # Process one file at a time
        ast = parse_makefile(filepath)
        ir = build_ir(ast)
        emit_cmake(ir)

        # Clear references to allow garbage collection
        del ast
        del ir
```

### Memory Profiling

```python
import tracemalloc

def profile_memory():
    """Profile memory usage."""
    tracemalloc.start()

    # Run conversion
    convert_project()

    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 1024 / 1024:.1f}MB")
    print(f"Peak memory: {peak / 1024 / 1024:.1f}MB")

    tracemalloc.stop()
```

### Optimization Tips

1. **Use generators** instead of lists when possible
2. **Delete large objects** when done
3. **Use `__slots__`** for classes with many instances
4. **Avoid circular references** that prevent GC

Example with `__slots__`:

```python
class Target:
    """Memory-efficient target representation."""
    __slots__ = ['name', 'type', 'sources', 'dependencies']

    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.sources = []
        self.dependencies = []
```

## Benchmarking

### Benchmark Suite

```python
# tests/benchmarks/test_performance.py
import pytest
import time

@pytest.mark.benchmark
def test_parse_performance(benchmark):
    """Benchmark parsing performance."""
    makefile = create_large_makefile(1000)  # 1000 targets

    result = benchmark(parse_makefile, makefile)

    assert len(result.rules) == 1000


@pytest.mark.benchmark
def test_expand_performance(benchmark):
    """Benchmark variable expansion."""
    context = create_context_with_variables(500)

    result = benchmark(expand_all_variables, context)

    assert len(result) == 500


def test_large_project_performance():
    """Test performance on large project."""
    start = time.time()

    convert_large_project()

    duration = time.time() - start
    assert duration < 60.0  # Should complete in under 1 minute
```

### Running Benchmarks

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare benchmarks
pytest tests/benchmarks/ --benchmark-compare

# Generate report
pytest tests/benchmarks/ --benchmark-autosave
```

### Regression Testing

Track performance over time:

```bash
# Save baseline
pytest tests/benchmarks/ --benchmark-save=baseline

# Compare against baseline
pytest tests/benchmarks/ --benchmark-compare=baseline

# Fail if regression
pytest tests/benchmarks/ --benchmark-compare=baseline --benchmark-fail=10%
```

## Scalability

### Horizontal Scaling

For very large projects, process in stages:

```bash
# Stage 1: Parse all Makefiles
gmake2cmake --stage parse --output parsed/

# Stage 2: Build IR
gmake2cmake --stage ir --input parsed/ --output ir/

# Stage 3: Emit CMake
gmake2cmake --stage emit --input ir/ --output cmake/
```

### Distributed Processing

For massive projects, distribute across machines:

```python
# coordinator.py
from distributed import Client

def distribute_conversion(makefile_groups):
    """Distribute conversion across workers."""
    client = Client('scheduler:8786')

    futures = client.map(convert_group, makefile_groups)
    results = client.gather(futures)

    return merge_results(results)
```

### Resource Limits

Set resource limits:

```yaml
# gmake2cmake.yaml
performance:
  max_memory_mb: 4096  # 4GB limit
  max_time_seconds: 300  # 5 minute timeout
  max_files: 1000  # Process at most 1000 files
```

### Scaling Guidelines

| Project Size | Workers | Memory | Cache |
|-------------|---------|---------|-------|
| Small | 1-2 | 256MB | Optional |
| Medium | 2-4 | 512MB-1GB | Recommended |
| Large | 4-8 | 1-4GB | Required |
| Very Large | 8+ | 4GB+ | Required |

## Performance Checklist

Before deploying for large projects:

- [ ] Enable parallel processing
- [ ] Enable caching
- [ ] Profile bottlenecks
- [ ] Optimize hot paths
- [ ] Set resource limits
- [ ] Monitor memory usage
- [ ] Test on representative data
- [ ] Benchmark against baseline
- [ ] Document performance characteristics

## See Also

- [Architecture Guide](architecture.md) - System design
- [Testing Guide](testing.md) - Performance testing
- [Configuration Guide](configuration.md) - Performance settings
