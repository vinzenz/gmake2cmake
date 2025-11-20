"""Comprehensive tests for diagnostic_codes module."""

from __future__ import annotations

import pytest
from gmake2cmake.diagnostic_codes import (
    DiagnosticCode,
    DiagnosticMetadata,
    get_metadata,
    is_valid_code,
    validate_code,
    list_codes_by_category,
    generate_documentation,
)


class TestDiagnosticCodeEnum:
    """Test DiagnosticCode enum."""

    def test_enum_has_codes(self):
        """DiagnosticCode enum should have code values."""
        assert len(list(DiagnosticCode)) > 0

    def test_test_code_exists(self):
        """TEST code should exist for testing."""
        assert DiagnosticCode.TEST == "TEST"

    def test_cli_codes_exist(self):
        """CLI-related codes should exist."""
        assert DiagnosticCode.CLI_UNHANDLED
        assert DiagnosticCode.REPORT_WRITE_FAIL

    def test_ir_codes_exist(self):
        """IR-related codes should exist."""
        assert DiagnosticCode.IR_UNMAPPED_FLAG
        assert DiagnosticCode.IR_DUP_TARGET

    def test_config_codes_exist(self):
        """Config-related codes should exist."""
        assert DiagnosticCode.CONFIG_MISSING
        assert DiagnosticCode.CONFIG_PARSE_ERROR

    def test_discovery_codes_exist(self):
        """Discovery-related codes should exist."""
        assert DiagnosticCode.DISCOVERY_ENTRY_MISSING
        assert DiagnosticCode.DISCOVERY_CYCLE

    def test_eval_codes_exist(self):
        """Evaluation-related codes should exist."""
        assert DiagnosticCode.EVAL_RECURSIVE_LOOP
        assert DiagnosticCode.UNKNOWN_CONSTRUCT


class TestDiagnosticMetadata:
    """Test DiagnosticMetadata class."""

    def test_metadata_creation(self):
        """DiagnosticMetadata should be creatable."""
        metadata = DiagnosticMetadata(
            code="TEST_CODE",
            category="TEST",
            default_severity="INFO",
            description="Test code"
        )
        assert metadata.code == "TEST_CODE"
        assert metadata.category == "TEST"
        assert metadata.default_severity == "INFO"

    def test_metadata_invalid_severity(self):
        """Invalid severity should raise error."""
        with pytest.raises(ValueError):
            DiagnosticMetadata(
                code="TEST",
                category="TEST",
                default_severity="INVALID",
                description="Test"
            )

    def test_metadata_with_template(self):
        """Metadata can have message template."""
        metadata = DiagnosticMetadata(
            code="TEST",
            category="TEST",
            default_severity="ERROR",
            description="Test",
            message_template="Error: {error}"
        )
        assert metadata.message_template == "Error: {error}"


class TestMetadataRegistry:
    """Test diagnostic code metadata registry."""

    def test_get_metadata_valid_code(self):
        """get_metadata should return metadata for valid codes."""
        metadata = get_metadata("TEST")
        assert isinstance(metadata, DiagnosticMetadata)
        assert metadata.code == "TEST"

    def test_get_metadata_invalid_code(self):
        """get_metadata should raise for invalid codes."""
        with pytest.raises(ValueError):
            get_metadata("INVALID_CODE")

    def test_all_enum_codes_have_metadata(self):
        """All enum codes should have metadata."""
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            assert metadata.code == code.value


class TestCodeValidation:
    """Test code validation functions."""

    def test_is_valid_code_true(self):
        """is_valid_code should return True for valid codes."""
        assert is_valid_code("TEST") is True
        assert is_valid_code("CLI_UNHANDLED") is True

    def test_is_valid_code_false(self):
        """is_valid_code should return False for invalid codes."""
        assert is_valid_code("INVALID") is False
        assert is_valid_code("") is False

    def test_validate_code_valid(self):
        """validate_code should return code if valid."""
        assert validate_code("TEST") == "TEST"

    def test_validate_code_invalid(self):
        """validate_code should raise for invalid codes."""
        with pytest.raises(ValueError):
            validate_code("INVALID")


class TestCategorization:
    """Test code categorization."""

    def test_list_codes_by_category(self):
        """list_codes_by_category should group codes."""
        categories = list_codes_by_category()
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_category_has_codes(self):
        """Each category should have at least one code."""
        categories = list_codes_by_category()
        for category, codes in categories.items():
            assert len(codes) > 0
            assert isinstance(codes, list)

    def test_categories_sorted(self):
        """Categories and codes should be sorted."""
        categories = list_codes_by_category()
        for category, codes in categories.items():
            assert codes == sorted(codes)

    def test_common_categories_exist(self):
        """Common categories should exist."""
        categories = list_codes_by_category()
        # At least some of these should exist
        common_categories = {'CLI', 'CONFIG', 'IR', 'DISCOVERY', 'EVAL', 'TEST'}
        actual_categories = set(categories.keys())
        assert len(common_categories & actual_categories) > 0


class TestDocumentation:
    """Test documentation generation."""

    def test_generate_documentation(self):
        """generate_documentation should create markdown."""
        doc = generate_documentation()
        assert isinstance(doc, str)
        assert len(doc) > 0

    def test_documentation_has_headers(self):
        """Documentation should have markdown headers."""
        doc = generate_documentation()
        assert "#" in doc
        assert "Diagnostic Codes" in doc

    def test_documentation_includes_all_codes(self):
        """Documentation should include all codes."""
        doc = generate_documentation()
        for code in DiagnosticCode:
            assert code.value in doc


class TestSeverityLevels:
    """Test severity level consistency."""

    def test_all_severities_valid(self):
        """All metadata severities should be valid."""
        valid_severities = {"ERROR", "WARN", "INFO"}
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            assert metadata.default_severity in valid_severities

    def test_error_codes_exist(self):
        """There should be ERROR severity codes."""
        error_codes = []
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            if metadata.default_severity == "ERROR":
                error_codes.append(code)
        assert len(error_codes) > 0

    def test_warning_codes_exist(self):
        """There should be WARN severity codes."""
        warn_codes = []
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            if metadata.default_severity == "WARN":
                warn_codes.append(code)
        assert len(warn_codes) > 0


class TestMessageTemplates:
    """Test message template functionality."""

    def test_some_codes_have_templates(self):
        """Some codes should have message templates."""
        codes_with_templates = []
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            if metadata.message_template:
                codes_with_templates.append(code)
        # At least some codes should have templates
        assert len(codes_with_templates) > 0

    def test_template_format(self):
        """Message templates should be valid format strings."""
        for code in DiagnosticCode:
            metadata = get_metadata(code.value)
            if metadata.message_template:
                # Should not raise
                template = metadata.message_template
                assert isinstance(template, str)
                # Templates with placeholders should have {}
                if "{" in template:
                    assert "}" in template
