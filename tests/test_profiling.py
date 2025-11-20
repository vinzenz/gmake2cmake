"""Tests for profiling module."""

from __future__ import annotations

import time

import pytest

from gmake2cmake.profiling import (
    disable_profiling,
    enable_profiling,
    get_metrics,
    is_profiling_enabled,
    profile_stage,
    reset_metrics,
    timed_block,
)


def test_profiling_disabled_by_default():
    """Test that profiling is disabled by default."""
    reset_metrics()
    assert not is_profiling_enabled()


def test_enable_disable_profiling():
    """Test enabling and disabling profiling."""
    reset_metrics()
    assert not is_profiling_enabled()

    enable_profiling()
    assert is_profiling_enabled()

    disable_profiling()
    assert not is_profiling_enabled()


def test_metrics_collection():
    """Test basic metrics collection."""
    reset_metrics()
    enable_profiling()

    metrics = get_metrics()
    metrics.add_timing("test_stage", 0.5)
    metrics.add_timing("test_stage", 0.3)

    assert metrics.stage_timings["test_stage"] == pytest.approx(0.8, abs=0.01)
    assert metrics.stage_counts["test_stage"] == 2

    disable_profiling()


def test_profile_stage_decorator():
    """Test @profile_stage decorator."""
    reset_metrics()
    enable_profiling()

    @profile_stage("slow_function")
    def slow_func():
        time.sleep(0.01)
        return 42

    result = slow_func()
    assert result == 42

    metrics = get_metrics()
    assert "slow_function" in metrics.stage_timings
    assert metrics.stage_timings["slow_function"] >= 0.01
    assert metrics.stage_counts["slow_function"] == 1

    disable_profiling()


def test_profile_stage_decorator_disabled():
    """Test that decorator doesn't add overhead when disabled."""
    reset_metrics()
    disable_profiling()

    @profile_stage("test")
    def quick_func():
        return "result"

    result = quick_func()
    assert result == "result"

    metrics = get_metrics()
    assert "test" not in metrics.stage_timings


def test_timed_block_context_manager():
    """Test timed_block context manager."""
    reset_metrics()
    enable_profiling()

    with timed_block("test_block"):
        time.sleep(0.01)

    metrics = get_metrics()
    assert "test_block" in metrics.stage_timings
    assert metrics.stage_timings["test_block"] >= 0.01

    disable_profiling()


def test_timed_block_disabled():
    """Test timed_block when profiling is disabled."""
    reset_metrics()
    disable_profiling()

    with timed_block("test"):
        time.sleep(0.001)

    metrics = get_metrics()
    assert "test" not in metrics.stage_timings


def test_multiple_stages():
    """Test profiling multiple different stages."""
    reset_metrics()
    enable_profiling()

    get_metrics().add_timing("stage1", 0.1)
    get_metrics().add_timing("stage2", 0.2)
    get_metrics().add_timing("stage3", 0.15)

    metrics = get_metrics()
    assert len(metrics.stage_timings) == 3
    assert metrics.stage_timings["stage1"] == pytest.approx(0.1, abs=0.01)
    assert metrics.stage_timings["stage2"] == pytest.approx(0.2, abs=0.01)
    assert metrics.stage_timings["stage3"] == pytest.approx(0.15, abs=0.01)

    disable_profiling()


def test_metrics_summary():
    """Test metrics.get_summary()."""
    reset_metrics()
    enable_profiling()

    get_metrics().add_timing("stage1", 0.5)
    get_metrics().add_timing("stage2", 0.3)

    summary = get_metrics().get_summary()
    assert "Performance Summary" in summary
    assert "stage1" in summary
    assert "stage2" in summary
    assert "0.800s" in summary or "0.8s" in summary  # May vary by formatting

    disable_profiling()


def test_reset_metrics():
    """Test reset_metrics clears all data."""
    reset_metrics()
    enable_profiling()

    get_metrics().add_timing("test", 1.0)
    assert get_metrics().stage_timings

    reset_metrics()
    assert not get_metrics().stage_timings
    assert not get_metrics().stage_counts

    disable_profiling()


def test_metrics_empty_summary():
    """Test get_summary with no metrics."""
    reset_metrics()
    summary = get_metrics().get_summary()
    assert "No profiling data" in summary
