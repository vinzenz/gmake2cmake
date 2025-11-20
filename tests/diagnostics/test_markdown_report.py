"""Tests for Markdown report generation."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.unknowns import UnknownConstructFactory
from gmake2cmake.markdown_reporter import (
    ConversionMetrics,
    MarkdownReporter,
    write_report,
)


def test_markdown_reporter_generates_report():
    """Test that reporter generates basic report."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "TEST", "Test error")
    add(collector, "WARN", "TEST", "Test warning")

    reporter = MarkdownReporter("TestProject")
    report = reporter.generate_report(collector, [])

    assert "TestProject" in report
    assert "Summary" in report
    assert "Statistics" in report
    assert "Diagnostics" in report


def test_markdown_reporter_includes_header():
    """Test that report includes header with project name."""
    collector = DiagnosticCollector()
    reporter = MarkdownReporter("MyProject")
    report = reporter.generate_report(collector, [])

    assert "# Makefile to CMake Conversion Report" in report
    assert "MyProject" in report
    assert "Generated:" in report


def test_markdown_reporter_groups_by_severity():
    """Test that diagnostics are grouped by severity."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "TEST", "error msg")
    add(collector, "WARN", "TEST", "warn msg")
    add(collector, "INFO", "TEST", "info msg")

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [])

    assert "### ERRORs" in report or "ERROR" in report
    assert "error msg" in report
    assert "warn msg" in report
    assert "info msg" in report


def test_markdown_reporter_handles_unknown_constructs():
    """Test report with unknown constructs."""
    collector = DiagnosticCollector()
    factory = UnknownConstructFactory()

    uc1 = factory.create(
        category="make_function",
        file="Makefile",
        raw_snippet="$(shell echo hi)",
        normalized_form="shell(echo hi)",
    )
    uc2 = factory.create(
        category="variable_reference",
        file="subdir/Makefile",
        raw_snippet="$(COMPLEX_VAR)",
        normalized_form="complex_var",
    )

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [uc1, uc2])

    assert "Unknown Constructs" in report
    assert "make_function" in report
    assert "variable_reference" in report
    assert "UC0001" in report
    assert "UC0002" in report


def test_markdown_reporter_statistics():
    """Test that statistics are correctly reported."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "CLI_UNHANDLED", "error 1")
    add(collector, "ERROR", "CLI_UNHANDLED", "error 2")  # same code
    add(collector, "WARN", "CONFIG_MISSING", "warning")

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [])

    assert "2" in report  # ERROR count
    assert "1" in report  # WARN count
    assert "CLI_UNHANDLED" in report
    assert "CONFIG_MISSING" in report


def test_markdown_reporter_recommendations():
    """Test that recommendations are generated."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "TEST", "Test error")

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [])

    assert "Recommendations" in report
    assert "errors" in report or "error" in report


def test_markdown_reporter_with_metrics():
    """Test report generation with provided metrics."""
    collector = DiagnosticCollector()
    metrics = ConversionMetrics(
        total_files=10,
        files_analyzed=8,
        total_targets=5,
        conversion_coverage_percent=85.0,
        error_count=1,
        warning_count=3,
        unknown_constructs_count=2,
    )

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [], metrics)

    assert "85.0" in report
    assert "Summary" in report


def test_write_report_to_file():
    """Test writing report to file."""
    with TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "report.md"

        collector = DiagnosticCollector()
        add(collector, "WARN", "TEST", "Test warning")

        write_report(report_path, collector, [], "TestProject")

        assert report_path.exists()
        content = report_path.read_text()
        assert "TestProject" in content
        assert "Summary" in content


def test_markdown_renderer_stability():
    """Test that report generation is stable across runs."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "CLI_UNHANDLED", "Error")
    add(collector, "WARN", "CONFIG_MISSING", "Warning")

    factory = UnknownConstructFactory()
    uc = factory.create(
        category="test",
        file="Makefile",
        raw_snippet="test",
    )

    reporter = MarkdownReporter("Test")
    report1 = reporter.generate_report(collector, [uc])
    report2 = reporter.generate_report(collector, [uc])

    # Reports should be similar in structure (though timestamps may differ)
    assert report1.count("Error") == report2.count("Error")
    assert report1.count("Warning") == report2.count("Warning")


def test_markdown_report_empty_diagnostics():
    """Test report generation with no diagnostics."""
    collector = DiagnosticCollector()
    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [])

    assert "# Makefile to CMake Conversion Report" in report
    assert "No diagnostics reported" in report


def test_markdown_report_with_locations():
    """Test that diagnostic locations are included."""
    collector = DiagnosticCollector()
    add(collector, "ERROR", "TEST", "Test error", location="Makefile:10:5")

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [])

    assert "Makefile:10:5" in report or "Makefile" in report


def test_markdown_reporter_deterministic_category_order():
    """Test that unknown construct categories are in deterministic order."""
    collector = DiagnosticCollector()
    factory = UnknownConstructFactory()

    # Create in random order
    uc_z = factory.create(category="zebra", file="Makefile", raw_snippet="z")
    uc_a = factory.create(category="apple", file="Makefile", raw_snippet="a")
    uc_m = factory.create(category="mango", file="Makefile", raw_snippet="m")

    reporter = MarkdownReporter("Test")
    report = reporter.generate_report(collector, [uc_z, uc_a, uc_m])

    apple_pos = report.find("apple")
    mango_pos = report.find("mango")
    zebra_pos = report.find("zebra")

    # Should be in alphabetical order
    assert apple_pos < mango_pos < zebra_pos
