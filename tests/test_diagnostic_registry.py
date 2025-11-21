"""Tests for the diagnostic code registry."""

from __future__ import annotations

import pytest

from gmake2cmake.diagnostic_codes import (
    DiagnosticCode,
    DiagnosticMetadata,
    generate_documentation,
    get_metadata,
    is_valid_code,
    list_codes_by_category,
    validate_code,
)


def test_diagnostic_code_enum_exists():
    """Test that all expected diagnostic codes exist."""
    assert DiagnosticCode.TEST.value == "TEST"
    assert DiagnosticCode.CLI_UNHANDLED.value == "CLI_UNHANDLED"
    assert DiagnosticCode.DISCOVERY_ENTRY_MISSING.value == "DISCOVERY_ENTRY_MISSING"
    assert DiagnosticCode.CONFIG_MISSING.value == "CONFIG_MISSING"


def test_diagnostic_metadata_structure():
    """Test that metadata has correct structure."""
    metadata = get_metadata("TEST")
    assert isinstance(metadata, DiagnosticMetadata)
    assert metadata.code == "TEST"
    assert metadata.category == "TEST"
    assert metadata.default_severity == "INFO"
    assert metadata.description


def test_get_metadata_for_all_codes():
    """Test that metadata exists for all enum codes."""
    for code in DiagnosticCode:
        metadata = get_metadata(code.value)
        assert metadata.code == code.value
        assert metadata.category in ["CLI", "CONFIG", "DISCOVERY", "EMIT", "EVAL", "IR", "TEST", "VALIDATION", "INTROSPECTION"]
        assert metadata.default_severity in ["ERROR", "WARN", "INFO"]


def test_metadata_validation():
    """Test that invalid metadata is rejected."""
    with pytest.raises(ValueError, match="Invalid severity"):
        DiagnosticMetadata(
            code="TEST_CODE",
            category="TEST",
            default_severity="INVALID",
            description="Test",
        )


def test_get_metadata_invalid_code():
    """Test that getting metadata for invalid code raises error."""
    with pytest.raises(ValueError, match="Unknown diagnostic code"):
        get_metadata("NONEXISTENT_CODE")


def test_is_valid_code():
    """Test code validation."""
    assert is_valid_code("TEST") is True
    assert is_valid_code("CLI_UNHANDLED") is True
    assert is_valid_code("NONEXISTENT") is False
    assert is_valid_code("") is False


def test_validate_code_valid():
    """Test code validation returns valid codes."""
    assert validate_code("TEST") == "TEST"
    assert validate_code("CONFIG_MISSING") == "CONFIG_MISSING"


def test_validate_code_invalid():
    """Test code validation raises for invalid codes."""
    with pytest.raises(ValueError, match="Invalid diagnostic code"):
        validate_code("NONEXISTENT")


def test_no_duplicate_codes():
    """Test that there are no duplicate codes in the registry."""
    # This is tested by the _validate_registry() call on module import
    # If duplicates existed, the module would fail to import
    codes = [code.value for code in DiagnosticCode]
    assert len(codes) == len(set(codes)), "Duplicate codes found in enum"


def test_all_categories_documented():
    """Test that all codes have associated category."""
    categories = list_codes_by_category()
    assert len(categories) > 0
    for category, codes in categories.items():
        assert len(codes) > 0
        for code in codes:
            metadata = get_metadata(code)
            assert metadata.category == category


def test_list_codes_by_category():
    """Test category listing."""
    categories = list_codes_by_category()
    expected_categories = ["CLI", "CONFIG", "DISCOVERY", "EMIT", "EVAL", "IR", "TEST", "VALIDATION", "INTROSPECTION"]
    assert set(categories.keys()) == set(expected_categories)

    # Verify some codes are in expected categories
    assert "TEST" in categories["TEST"]
    assert "CLI_UNHANDLED" in categories["CLI"]
    assert "CONFIG_MISSING" in categories["CONFIG"]
    assert "DISCOVERY_ENTRY_MISSING" in categories["DISCOVERY"]


def test_generate_documentation():
    """Test documentation generation."""
    doc = generate_documentation()
    assert "# Diagnostic Codes" in doc
    assert "## CLI" in doc
    assert "## CONFIG" in doc
    assert "`TEST`" in doc
    assert "`CLI_UNHANDLED`" in doc
    assert "Default Severity" in doc
    assert "Description" in doc
    # Check for some message templates
    assert "Message Template" in doc


def test_documentation_includes_all_codes():
    """Test that generated documentation includes all codes."""
    doc = generate_documentation()
    for code in DiagnosticCode:
        assert f"`{code.value}`" in doc


def test_documentation_format():
    """Test that documentation is properly formatted markdown."""
    doc = generate_documentation()
    lines = doc.split("\n")
    assert lines[0] == "# Diagnostic Codes"
    # Check for section headers
    assert any(line.startswith("## ") for line in lines), "Missing category headers"
    # Check for code headers
    assert any(line.startswith("### ") for line in lines), "Missing code headers"


def test_severity_levels_valid():
    """Test that all metadata uses valid severity levels."""
    valid_severities = {"ERROR", "WARN", "INFO"}
    for code in DiagnosticCode:
        metadata = get_metadata(code.value)
        assert metadata.default_severity in valid_severities


def test_metadata_description_not_empty():
    """Test that all codes have descriptions."""
    for code in DiagnosticCode:
        metadata = get_metadata(code.value)
        assert metadata.description and metadata.description.strip()
