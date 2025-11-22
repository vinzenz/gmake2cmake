"""Tests for reporting helpers and introspection summary serialization."""

from __future__ import annotations

import json
from pathlib import Path

from gmake2cmake import cli
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.builder import Project, ProjectGlobalConfig, Target
from tests.conftest import FakeFS


def _project_with_targets() -> Project:
    cfg = ProjectGlobalConfig(
        vars={},
        flags={},
        defines=[],
        includes=[],
        feature_toggles={},
        sources=[],
    )
    targets = [
        Target(
            artifact="app",
            name="app",
            alias=None,
            type="executable",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=[],
            introspection_commands=["echo app"],
            validated_by_introspection=True,
        ),
        Target(
            artifact="lib",
            name="lib",
            alias=None,
            type="library",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=[],
            introspection_commands=["echo lib"],
            validated_by_introspection=False,
        ),
        Target(
            artifact="util",
            name="util",
            alias=None,
            type="executable",
            sources=[],
            include_dirs=[],
            defines=[],
            compile_options=[],
            link_options=[],
            link_libs=[],
            deps=[],
            introspection_commands=["echo util"],
            validated_by_introspection=True,
            origin="introspection",
        ),
    ]
    return Project(
        name="proj",
        version=None,
        namespace="proj",
        languages=["C"],
        targets=targets,
        project_config=cfg,
    )


def test_compute_introspection_summary_counts():
    diagnostics = DiagnosticCollector()
    add(diagnostics, "WARN", "INTROSPECTION_MISMATCH", "differs")
    add(diagnostics, "WARN", "INTROSPECTION_FAILED", "truncated")

    project = _project_with_targets()
    summary = cli._compute_introspection_summary(True, project, diagnostics)

    assert summary.enabled is True
    assert summary.targets_total == 3
    assert summary.validated_count == 2
    assert summary.modified_count == 2  # mismatch + introspection-only
    assert summary.mismatch_count == 1
    assert summary.failure_count == 1
    assert summary.added_count == 1


def test_write_report_serializes_introspection_summary():
    diagnostics = DiagnosticCollector()
    fs = FakeFS()
    summary = cli.IntrospectionSummary(
        enabled=True,
        targets_total=2,
        validated_count=1,
        modified_count=1,
        mismatch_count=0,
        failure_count=0,
        added_count=0,
    )

    cli._write_report(Path("/out"), diagnostics, fs, [], project_name="proj", introspection_summary=summary)

    report_path = next(path for path in fs.store if path.name == "report.json")
    payload = json.loads(fs.store[report_path])
    assert payload["introspection"]["introspection_enabled"] is True
    assert payload["introspection"]["validated_count"] == 1
    assert payload["introspection"]["modified_count"] == 1

    markdown_path = next(path for path in fs.store if path.name == "report.md")
    assert "Introspection" in fs.store[markdown_path]
