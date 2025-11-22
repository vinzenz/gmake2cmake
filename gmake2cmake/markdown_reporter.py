"""Markdown report generator for conversion diagnostics and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.ir.unknowns import UnknownConstruct
from gmake2cmake.utils.ordering import sort_diagnostics


@dataclass
class ConversionMetrics:
    """Metrics about the conversion process."""

    total_files: int = 0
    files_analyzed: int = 0
    total_targets: int = 0
    conversion_coverage_percent: float = 0.0
    error_count: int = 0
    warning_count: int = 0
    unknown_constructs_count: int = 0


class MarkdownReporter:
    """Generate human-readable Markdown reports from diagnostics and unknowns."""

    def __init__(self, project_name: str = "Unnamed Project") -> None:
        """Initialize the reporter.

        Args:
            project_name: Name of the project being converted.
        """
        self.project_name = project_name
        self.generated_at = datetime.now()

    def generate_report(
        self,
        diagnostics_collector: DiagnosticCollector,
        unknown_constructs: List[UnknownConstruct],
        metrics: Optional[ConversionMetrics] = None,
        introspection_summary: Optional[dict] = None,
    ) -> str:
        """Generate a complete Markdown report.

        Args:
            diagnostics_collector: Collector with all diagnostics.
            unknown_constructs: List of unknown constructs encountered.
            metrics: Optional metrics about the conversion.
            introspection_summary: Optional summary of make introspection results.

        Returns:
            Markdown-formatted report string.
        """
        if metrics is None:
            metrics = self._calculate_metrics(diagnostics_collector, unknown_constructs)

        sections = [
            self._header_section(),
            self._summary_section(metrics, introspection_summary),
            self._statistics_section(diagnostics_collector, unknown_constructs),
            self._diagnostics_section(diagnostics_collector),
            self._unknown_constructs_section(unknown_constructs),
            self._recommendations_section(diagnostics_collector, unknown_constructs),
        ]

        return "\n\n".join(filter(None, sections))

    def _header_section(self) -> str:
        """Generate the header section."""
        return f"""# Makefile to CMake Conversion Report

**Project:** {self.project_name}
**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _summary_section(self, metrics: ConversionMetrics, introspection_summary: Optional[dict] = None) -> str:
        """Generate the summary section."""
        lines = [
            f"- **Files Analyzed:** {metrics.files_analyzed} / {metrics.total_files}",
            f"- **Targets Found:** {metrics.total_targets}",
            f"- **Conversion Coverage:** {metrics.conversion_coverage_percent:.1f}%",
            f"- **Errors:** {metrics.error_count}",
            f"- **Warnings:** {metrics.warning_count}",
            f"- **Unknown Constructs:** {metrics.unknown_constructs_count}",
        ]
        if introspection_summary is not None:
            status = "enabled" if introspection_summary.get("introspection_enabled") else "disabled"
            lines.append(f"- **Introspection:** {status}")
            if introspection_summary.get("introspection_enabled"):
                validated = introspection_summary.get("validated_count", 0)
                total = introspection_summary.get("targets_total", 0)
                modified = introspection_summary.get("modified_count", 0)
                mismatches = introspection_summary.get("mismatch_count", 0)
                failures = introspection_summary.get("failure_count", 0)
                lines.append(f"  - Validated Targets: {validated}/{total}")
                lines.append(f"  - Modified Targets: {modified}")
                lines.append(f"  - Mismatches: {mismatches}")
                lines.append(f"  - Failures: {failures}")

        return "## Summary\n\n" + "\n".join(lines) + "\n"

    def _statistics_section(
        self, diagnostics_collector: DiagnosticCollector, unknown_constructs: List[UnknownConstruct]
    ) -> str:
        """Generate the statistics section."""
        diags = diagnostics_collector.diagnostics
        severity_counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
        code_counts: dict[str, int] = {}

        for diag in diags:
            severity_counts[diag.severity] = severity_counts.get(diag.severity, 0) + 1
            code_counts[diag.code] = code_counts.get(diag.code, 0) + 1

        stats = f"""## Statistics

### Diagnostic Counts by Severity

| Severity | Count |
|----------|-------|
| ERROR    | {severity_counts.get('ERROR', 0)} |
| WARN     | {severity_counts.get('WARN', 0)} |
| INFO     | {severity_counts.get('INFO', 0)} |

### Diagnostic Codes

| Code | Count |
|------|-------|
"""
        for code in sorted(code_counts.keys()):
            stats += f"| {code} | {code_counts[code]} |\n"

        if unknown_constructs:
            stats += "\n### Unknown Constructs by Category\n\n| Category | Count |\n|----------|-------|\n"
            category_counts: dict[str, int] = {}
            for uc in unknown_constructs:
                category_counts[uc.category] = category_counts.get(uc.category, 0) + 1
            for category in sorted(category_counts.keys()):
                stats += f"| {category} | {category_counts[category]} |\n"

        return stats

    def _diagnostics_section(self, diagnostics_collector: DiagnosticCollector) -> str:
        """Generate the diagnostics section."""
        diags = sort_diagnostics(diagnostics_collector.diagnostics)

        if not diags:
            return "## Diagnostics\n\nNo diagnostics reported."

        section = "## Diagnostics\n\n"
        current_severity = None

        for diag in diags:
            if diag.severity != current_severity:
                current_severity = diag.severity
                section += f"\n### {current_severity}s\n\n"

            location = f" ({diag.location})" if diag.location else ""
            origin = f" [from {diag.origin}]" if diag.origin else ""
            section += f"- **{diag.code}:** {diag.message}{location}{origin}\n"

        return section

    def _unknown_constructs_section(self, unknown_constructs: List[UnknownConstruct]) -> str:
        """Generate the unknown constructs section."""
        if not unknown_constructs:
            return "## Unknown Constructs\n\nAll constructs were successfully parsed."

        section = "## Unknown Constructs\n\n"
        section += "The following Make constructs could not be automatically converted:\n\n"

        # Group by category
        by_category: dict[str, list] = {}
        for uc in unknown_constructs:
            if uc.category not in by_category:
                by_category[uc.category] = []
            by_category[uc.category].append(uc)

        for category in sorted(by_category.keys()):
            section += f"### {category}\n\n"
            for uc in by_category[category]:
                section += f"**{uc.id}** ({uc.file}:{uc.line})\n\n"
                section += f"```\n{uc.raw_snippet}\n```\n\n"
                if uc.suggested_action != "skip":
                    section += f"**Action:** {uc.suggested_action}\n\n"
                if uc.context:
                    section += "**Context:**\n"
                    for key, values in uc.context.items():
                        section += f"- {key}: {', '.join(values)}\n"
                    section += "\n"

        return section

    def _recommendations_section(
        self, diagnostics_collector: DiagnosticCollector, unknown_constructs: List[UnknownConstruct]
    ) -> str:
        """Generate actionable recommendations."""
        recommendations = []
        recommendations.extend(self._recommend_error_actions(diagnostics_collector))
        recommendations.extend(self._recommend_unknown_actions(unknown_constructs))
        recommendations.extend(self._recommend_warning_actions(diagnostics_collector))
        if not recommendations:
            return "## Recommendations\n\nNo issues found - conversion appears to be complete."
        return "## Recommendations\n\n" + "\n".join(recommendations)

    def _recommend_error_actions(self, diagnostics_collector: DiagnosticCollector) -> List[str]:
        errors = [d for d in diagnostics_collector.diagnostics if d.severity == "ERROR"]
        if not errors:
            return []
        return [
            "- **Address all errors** before proceeding with conversion",
            f"  - {len(errors)} error(s) found that must be resolved",
        ]

    def _recommend_unknown_actions(self, unknown_constructs: List[UnknownConstruct]) -> List[str]:
        if not unknown_constructs:
            return []
        recommendations = ["- **Review unknown constructs** for manual conversion requirements"]
        manual_review = [uc for uc in unknown_constructs if uc.suggested_action == "manual_review"]
        if manual_review:
            recommendations.append(f"  - {len(manual_review)} construct(s) require manual review")
        return recommendations

    def _recommend_warning_actions(self, diagnostics_collector: DiagnosticCollector) -> List[str]:
        warnings = [d for d in diagnostics_collector.diagnostics if d.severity == "WARN"]
        if not warnings:
            return []
        return [
            "- **Investigate warnings** for potential issues",
            f"  - {len(warnings)} warning(s) found",
        ]

    def _calculate_metrics(
        self,
        diagnostics_collector: DiagnosticCollector,
        unknown_constructs: List[UnknownConstruct],
    ) -> ConversionMetrics:
        """Calculate conversion metrics from diagnostics and unknowns."""
        error_count = sum(1 for d in diagnostics_collector.diagnostics if d.severity == "ERROR")
        warning_count = sum(1 for d in diagnostics_collector.diagnostics if d.severity == "WARN")

        return ConversionMetrics(
            error_count=error_count,
            warning_count=warning_count,
            unknown_constructs_count=len(unknown_constructs),
        )


def write_report(
    report_path: Path,
    diagnostics_collector: DiagnosticCollector,
    unknown_constructs: List[UnknownConstruct],
    project_name: str = "Unnamed Project",
    metrics: Optional[ConversionMetrics] = None,
    introspection_summary: Optional[dict] = None,
) -> None:
    """Write a Markdown report to disk.

    Args:
        report_path: Path where to write the report.
        diagnostics_collector: Collector with all diagnostics.
        unknown_constructs: List of unknown constructs.
        project_name: Name of the project.
        metrics: Optional metrics about the conversion.
        introspection_summary: Optional summary of make introspection results.
    """
    reporter = MarkdownReporter(project_name)
    report_content = reporter.generate_report(
        diagnostics_collector, unknown_constructs, metrics, introspection_summary=introspection_summary
    )
    report_path.write_text(report_content, encoding="utf-8")
