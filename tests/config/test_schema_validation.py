"""Tests for configuration schema validation."""

from __future__ import annotations

from gmake2cmake.diagnostics import DiagnosticCollector
from gmake2cmake.schema_validator import (
    _basic_config_validation,
    generate_config_template,
    load_schema,
    validate_config_schema,
)


def test_load_schema():
    """Test that schema can be loaded."""
    schema = load_schema()
    assert schema is not None
    assert "$schema" in schema or "title" in schema or "type" in schema
    assert "properties" in schema


def test_validate_empty_config():
    """Test validation of empty configuration."""
    collector = DiagnosticCollector()
    result = validate_config_schema({}, collector)
    # Empty config should be valid
    assert result is True


def test_validate_minimal_config():
    """Test validation of minimal valid configuration."""
    config = {"project_name": "test_project"}
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is True


def test_validate_full_config():
    """Test validation of complete configuration."""
    config = {
        "project_name": "full_project",
        "version": "1.0.0",
        "namespace": "FullProject",
        "languages": ["C", "CXX"],
        "flag_mappings": {"-O2": "-O3"},
        "ignore_paths": ["build/", ".git/"],
        "packaging_enabled": True,
        "strict": False,
        "error_recovery_enabled": True,
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is True


def test_validate_invalid_type():
    """Test validation catches invalid types."""
    config = {"project_name": 123}  # Should be string
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    # Should fail or at least detect the issue
    assert result is False or any("project_name" in d.message for d in collector.diagnostics)


def test_validate_invalid_language():
    """Test validation catches invalid language."""
    config = {
        "project_name": "test",
        "languages": ["C", "INVALID_LANG"],
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    # Should either fail or warn about invalid language
    # The schema validation behavior depends on whether jsonschema is available
    assert result is False or any("language" in d.message.lower() for d in collector.diagnostics)


def test_validate_target_mappings():
    """Test validation of target mapping configurations."""
    config = {
        "project_name": "test",
        "target_mappings": {
            "mylib": {
                "dest_name": "MyLib",
                "type_override": "library",
                "include_dirs": ["inc"],
            }
        },
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is True


def test_validate_invalid_target_type():
    """Test validation of invalid target type."""
    config = {
        "project_name": "test",
        "target_mappings": {
            "mylib": {
                "dest_name": "MyLib",
                "type_override": "invalid_type",
            }
        },
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    # Should either fail or warn about invalid type
    assert result is False or any("type" in d.message.lower() for d in collector.diagnostics)


def test_validate_link_overrides():
    """Test validation of link override configurations."""
    config = {
        "project_name": "test",
        "link_overrides": {
            "libz": {
                "classification": "imported",
                "imported_target": "ZLIB::ZLIB",
            }
        },
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is True


def test_validate_invalid_classification():
    """Test validation of invalid classification."""
    config = {
        "project_name": "test",
        "link_overrides": {
            "libz": {
                "classification": "invalid_class",
            }
        },
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is False or any("classification" in d.message.lower() for d in collector.diagnostics)


def test_basic_validation_invalid_languages_type():
    """Test basic validation detects invalid languages type."""
    config = {"languages": "C,CXX"}  # Should be list
    collector = DiagnosticCollector()
    result = _basic_config_validation(config, collector)
    assert result is False


def test_basic_validation_invalid_dict_type():
    """Test basic validation detects invalid dictionary types."""
    config = {"target_mappings": "invalid"}
    collector = DiagnosticCollector()
    result = _basic_config_validation(config, collector)
    assert result is False


def test_basic_validation_invalid_boolean():
    """Test basic validation detects invalid boolean types."""
    config = {"packaging_enabled": "yes"}  # Should be boolean
    collector = DiagnosticCollector()
    result = _basic_config_validation(config, collector)
    assert result is False


def test_generate_config_template():
    """Test that config template can be generated."""
    template = generate_config_template()
    assert template is not None
    assert len(template) > 0
    assert "project_name" in template
    assert "languages" in template
    assert "target_mappings" in template


def test_config_template_includes_examples():
    """Test that template includes example configurations."""
    template = generate_config_template()
    assert "my_project" in template or "example" in template.lower()
    assert "yaml" in template
    assert "FLAG" in template.upper() or "flag" in template.lower()


def test_custom_rules_validation():
    """Test validation of custom rules."""
    config = {
        "project_name": "test",
        "custom_rules": {
            "my_rule": {
                "match": "pattern",
                "handler": "module.handler",
            }
        },
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    assert result is True


def test_validate_unknown_key_warning():
    """Test that unknown keys trigger warning."""
    config = {
        "project_name": "test",
        "unknown_field": "value",
    }
    collector = DiagnosticCollector()
    result = validate_config_schema(config, collector)
    # Should produce a warning or error about unknown_field
    assert any("unknown" in d.message.lower() for d in collector.diagnostics) or result is False
