"""Comprehensive tests for types module."""

from __future__ import annotations

import pytest
from gmake2cmake.types import DiagnosticDict


class TestDiagnosticDict:
    """Test DiagnosticDict TypedDict."""

    def test_diagnostic_dict_creation(self):
        """DiagnosticDict can be created with required fields."""
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "TEST_ERROR",
            "message": "Test error message",
        }
        assert diag["severity"] == "ERROR"
        assert diag["code"] == "TEST_ERROR"
        assert diag["message"] == "Test error message"

    def test_diagnostic_dict_with_location(self):
        """DiagnosticDict can include location."""
        diag: DiagnosticDict = {
            "severity": "WARN",
            "code": "TEST_WARN",
            "message": "Warning",
            "location": "test.mk:10",
        }
        assert diag.get("location") == "test.mk:10"

    def test_diagnostic_dict_with_origin(self):
        """DiagnosticDict can include origin."""
        diag: DiagnosticDict = {
            "severity": "INFO",
            "code": "TEST_INFO",
            "message": "Info",
            "origin": "parser",
        }
        assert diag.get("origin") == "parser"

    def test_diagnostic_dict_all_fields(self):
        """DiagnosticDict can have all fields."""
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "FULL_TEST",
            "message": "Full test",
            "location": "file.mk:20:5",
            "origin": "evaluator",
        }
        assert len(diag) == 5

    def test_diagnostic_dict_optional_fields(self):
        """Optional fields can be None."""
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "TEST",
            "message": "Test",
            "location": None,
            "origin": None,
        }
        assert diag["location"] is None
        assert diag["origin"] is None


class TestDiagnosticDictValidation:
    """Test validation scenarios for DiagnosticDict."""

    def test_severity_values(self):
        """Common severity values should work."""
        for severity in ["ERROR", "WARN", "INFO"]:
            diag: DiagnosticDict = {
                "severity": severity,
                "code": "TEST",
                "message": "Test",
            }
            assert diag["severity"] == severity

    def test_code_values(self):
        """Various code values should work."""
        codes = ["TEST_ERROR", "PARSE_FAIL", "CONFIG_MISSING"]
        for code in codes:
            diag: DiagnosticDict = {
                "severity": "ERROR",
                "code": code,
                "message": "Test",
            }
            assert diag["code"] == code

    def test_message_values(self):
        """Various message values should work."""
        messages = [
            "Simple message",
            "Message with 'quotes'",
            "Message with\nnewline",
        ]
        for msg in messages:
            diag: DiagnosticDict = {
                "severity": "ERROR",
                "code": "TEST",
                "message": msg,
            }
            assert diag["message"] == msg


class TestDiagnosticDictUsage:
    """Test realistic usage of DiagnosticDict."""

    def test_collect_diagnostics(self):
        """Can collect multiple diagnostics in list."""
        diagnostics: list[DiagnosticDict] = []

        diagnostics.append({
            "severity": "ERROR",
            "code": "E001",
            "message": "Error 1",
        })

        diagnostics.append({
            "severity": "WARN",
            "code": "W001",
            "message": "Warning 1",
            "location": "file.mk:10",
        })

        assert len(diagnostics) == 2
        assert diagnostics[0]["severity"] == "ERROR"
        assert diagnostics[1]["severity"] == "WARN"

    def test_filter_by_severity(self):
        """Can filter diagnostics by severity."""
        diagnostics: list[DiagnosticDict] = [
            {"severity": "ERROR", "code": "E1", "message": "Err 1"},
            {"severity": "WARN", "code": "W1", "message": "Warn 1"},
            {"severity": "ERROR", "code": "E2", "message": "Err 2"},
        ]

        errors = [d for d in diagnostics if d["severity"] == "ERROR"]
        assert len(errors) == 2

    def test_format_diagnostic(self):
        """Can format diagnostic for output."""
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "TEST_ERROR",
            "message": "Something failed",
            "location": "test.mk:42",
        }

        formatted = f"[{diag['code']}] {diag['severity']}: {diag['message']}"
        assert "TEST_ERROR" in formatted
        assert "ERROR" in formatted
        assert "Something failed" in formatted

    def test_update_diagnostic(self):
        """Can update diagnostic fields."""
        diag: DiagnosticDict = {
            "severity": "WARN",
            "code": "TEST",
            "message": "Initial message",
        }

        # Update message
        diag["message"] = "Updated message"
        assert diag["message"] == "Updated message"

        # Add location
        diag["location"] = "file.mk:10"
        assert diag["location"] == "file.mk:10"


class TestDiagnosticDictEdgeCases:
    """Test edge cases for DiagnosticDict."""

    def test_empty_message(self):
        """Empty message should be allowed."""
        diag: DiagnosticDict = {
            "severity": "INFO",
            "code": "TEST",
            "message": "",
        }
        assert diag["message"] == ""

    def test_long_message(self):
        """Long messages should work."""
        long_msg = "A" * 1000
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "TEST",
            "message": long_msg,
        }
        assert len(diag["message"]) == 1000

    def test_unicode_in_message(self):
        """Unicode characters in message should work."""
        diag: DiagnosticDict = {
            "severity": "ERROR",
            "code": "TEST",
            "message": "Error with unicode: 你好 мир 🎉",
        }
        assert "你好" in diag["message"]

    def test_location_formats(self):
        """Various location formats should work."""
        locations = [
            "file.mk:10",
            "path/to/file.mk:20:5",
            "/absolute/path/file.mk:100",
        ]
        for loc in locations:
            diag: DiagnosticDict = {
                "severity": "ERROR",
                "code": "TEST",
                "message": "Test",
                "location": loc,
            }
            assert diag["location"] == loc
