"""Comprehensive tests for constants module."""

from __future__ import annotations

from gmake2cmake.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROJECT_NAME,
    DEFAULT_SOURCE_DIR,
    GLOBAL_CONFIG_FILENAMES,
    REPORT_JSON_FILENAME,
    REPORT_MD_FILENAME,
    VALID_CMAKE_STATUSES,
    VALID_CONFIG_TARGET_TYPES,
    VALID_DIAGNOSTIC_SEVERITIES,
    VALID_LINK_CLASSIFICATIONS,
    VALID_SUGGESTED_ACTIONS,
    VALID_TARGET_TYPES,
    VALID_VISIBILITY_LEVELS,
)


class TestDefaultConstants:
    """Test default constant values."""

    def test_default_source_dir(self):
        """Default source directory should be current dir."""
        assert isinstance(DEFAULT_SOURCE_DIR, str)
        assert DEFAULT_SOURCE_DIR == "."

    def test_default_output_dir(self):
        """Default output directory should be a string."""
        assert isinstance(DEFAULT_OUTPUT_DIR, str)
        assert len(DEFAULT_OUTPUT_DIR) > 0
        assert "cmake" in DEFAULT_OUTPUT_DIR.lower()

    def test_default_project_name(self):
        """Default project name should be a string."""
        assert isinstance(DEFAULT_PROJECT_NAME, str)
        assert len(DEFAULT_PROJECT_NAME) > 0

    def test_report_filenames(self):
        """Report filenames should be properly named."""
        assert isinstance(REPORT_JSON_FILENAME, str)
        assert REPORT_JSON_FILENAME.endswith('.json')
        assert isinstance(REPORT_MD_FILENAME, str)
        assert REPORT_MD_FILENAME.endswith('.md')


class TestValidSets:
    """Test validation sets."""

    def test_valid_target_types(self):
        """Valid target types should be a set of strings."""
        assert isinstance(VALID_TARGET_TYPES, set)
        assert len(VALID_TARGET_TYPES) > 0
        assert "executable" in VALID_TARGET_TYPES
        assert "static" in VALID_TARGET_TYPES
        assert "shared" in VALID_TARGET_TYPES

    def test_valid_config_target_types(self):
        """Valid config target types should include None."""
        assert isinstance(VALID_CONFIG_TARGET_TYPES, set)
        assert None in VALID_CONFIG_TARGET_TYPES
        assert "executable" in VALID_CONFIG_TARGET_TYPES

    def test_valid_visibility_levels(self):
        """Valid visibility levels should include CMAKE levels."""
        assert isinstance(VALID_VISIBILITY_LEVELS, set)
        assert "PUBLIC" in VALID_VISIBILITY_LEVELS
        assert "PRIVATE" in VALID_VISIBILITY_LEVELS
        assert "INTERFACE" in VALID_VISIBILITY_LEVELS

    def test_valid_link_classifications(self):
        """Valid link classifications should be defined."""
        assert isinstance(VALID_LINK_CLASSIFICATIONS, set)
        assert len(VALID_LINK_CLASSIFICATIONS) > 0
        assert "internal" in VALID_LINK_CLASSIFICATIONS or "external" in VALID_LINK_CLASSIFICATIONS

    def test_valid_cmake_statuses(self):
        """Valid CMake statuses should be defined."""
        assert isinstance(VALID_CMAKE_STATUSES, set)
        assert len(VALID_CMAKE_STATUSES) > 0

    def test_valid_suggested_actions(self):
        """Valid suggested actions should be defined."""
        assert isinstance(VALID_SUGGESTED_ACTIONS, set)
        assert len(VALID_SUGGESTED_ACTIONS) > 0
        assert "manual_review" in VALID_SUGGESTED_ACTIONS

    def test_valid_diagnostic_severities(self):
        """Valid diagnostic severities should include ERROR, WARN, INFO."""
        assert isinstance(VALID_DIAGNOSTIC_SEVERITIES, set)
        assert "ERROR" in VALID_DIAGNOSTIC_SEVERITIES
        assert "WARN" in VALID_DIAGNOSTIC_SEVERITIES
        assert "INFO" in VALID_DIAGNOSTIC_SEVERITIES


class TestGlobalConfigFilenames:
    """Test global config filename patterns."""

    def test_config_filenames_list(self):
        """Config filenames should be a list of strings."""
        assert isinstance(GLOBAL_CONFIG_FILENAMES, list)
        assert len(GLOBAL_CONFIG_FILENAMES) > 0
        for filename in GLOBAL_CONFIG_FILENAMES:
            assert isinstance(filename, str)
            assert len(filename) > 0

    def test_config_filenames_yaml(self):
        """Config filenames should include yaml files."""
        yaml_files = [f for f in GLOBAL_CONFIG_FILENAMES if 'yaml' in f.lower()]
        assert len(yaml_files) > 0


class TestConstantConsistency:
    """Test consistency between related constants."""

    def test_target_types_subset(self):
        """Config target types should be superset of target types."""
        non_none_config_types = VALID_CONFIG_TARGET_TYPES - {None}
        assert VALID_TARGET_TYPES == non_none_config_types

    def test_visibility_includes_none(self):
        """Visibility levels should allow None for defaults."""
        assert None in VALID_VISIBILITY_LEVELS

    def test_config_target_types_includes_none(self):
        """Config target types should allow None override."""
        assert None in VALID_CONFIG_TARGET_TYPES
