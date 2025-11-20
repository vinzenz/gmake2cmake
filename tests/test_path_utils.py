"""Tests for path validation utilities."""

from __future__ import annotations

import pytest

from gmake2cmake.path_utils import (
    is_path_absolute,
    is_valid_path,
    join_paths,
    normalize_glob_pattern,
    validate_path,
    validate_paths,
)


def test_validate_path_basic():
    """Test basic path validation."""
    result = validate_path("src/main.c")
    assert result == "src/main.c"


def test_validate_path_normalizes_backslash():
    """Test that backslashes are normalized."""
    result = validate_path("src\\main.c")
    assert result == "src/main.c"
    assert "\\" not in result


def test_validate_path_strips_trailing_slash():
    """Test that trailing slashes are stripped."""
    result = validate_path("src/")
    assert result == "src"


def test_validate_path_empty_raises():
    """Test that empty paths raise ValueError."""
    with pytest.raises(ValueError, match="empty"):
        validate_path("")


def test_validate_path_whitespace_only_raises():
    """Test that whitespace-only paths raise ValueError."""
    with pytest.raises(ValueError, match="empty"):
        validate_path("   ")


def test_validate_path_traversal_blocked():
    """Test that path traversal is blocked by default."""
    with pytest.raises(ValueError, match="traversal"):
        validate_path("../parent/file.c")


def test_validate_path_traversal_allowed():
    """Test that path traversal can be allowed."""
    result = validate_path("../parent/file.c", allow_traversal=True)
    assert result == "../parent/file.c"


def test_validate_path_null_bytes_blocked():
    """Test that null bytes are blocked."""
    with pytest.raises(ValueError, match="Null bytes"):
        validate_path("src/\x00/file.c")


def test_validate_path_allow_empty():
    """Test allowing empty paths."""
    result = validate_path("", allow_empty=True)
    assert result == ""


def test_validate_paths_list():
    """Test validating a list of paths."""
    paths = ["src/", "include/", "tests/"]
    result = validate_paths(paths)
    assert result == ["src", "include", "tests"]


def test_validate_paths_deduplicates():
    """Test that duplicate paths are removed."""
    paths = ["src/", "src", "src/"]
    result = validate_paths(paths)
    assert result == ["src"]


def test_validate_paths_with_invalid_raises():
    """Test that invalid paths in list raise ValueError."""
    paths = ["src/", "../invalid/"]
    with pytest.raises(ValueError, match="traversal"):
        validate_paths(paths)


def test_validate_paths_allow_traversal():
    """Test validating paths with traversal allowed."""
    paths = ["../parent/", "src/"]
    result = validate_paths(paths, allow_traversal=True)
    assert "../parent" in result
    assert "src" in result


def test_is_valid_path_true():
    """Test is_valid_path returns True for valid paths."""
    assert is_valid_path("src/file.c") is True
    assert is_valid_path("build/output/") is True


def test_is_valid_path_false():
    """Test is_valid_path returns False for invalid paths."""
    assert is_valid_path("") is False
    assert is_valid_path("../invalid") is False
    assert is_valid_path("src/\x00/file") is False


def test_normalize_glob_pattern():
    """Test glob pattern normalization."""
    result = normalize_glob_pattern("src/**/*.c")
    assert result == "src/**/*.c"
    assert "\\" not in result


def test_normalize_glob_pattern_empty_raises():
    """Test that empty patterns raise ValueError."""
    with pytest.raises(ValueError, match="empty"):
        normalize_glob_pattern("")


def test_normalize_glob_pattern_null_bytes_raises():
    """Test that null bytes in patterns raise ValueError."""
    with pytest.raises(ValueError, match="Null bytes"):
        normalize_glob_pattern("src/**\x00/*")


def test_is_path_absolute_unix():
    """Test absolute path detection on Unix."""
    assert is_path_absolute("/usr/bin") is True
    assert is_path_absolute("//network/share") is True


def test_is_path_absolute_windows():
    """Test absolute path detection on Windows."""
    assert is_path_absolute("C:/Users/") is True
    assert is_path_absolute("D:\\Projects") is True


def test_is_path_absolute_relative():
    """Test relative path detection."""
    assert is_path_absolute("src/file") is False
    assert is_path_absolute("../parent") is False
    assert is_path_absolute("./current") is False


def test_join_paths_basic():
    """Test joining path parts."""
    result = join_paths("src", "include")
    assert result == "src/include"


def test_join_paths_multiple():
    """Test joining multiple path parts."""
    result = join_paths("src", "core", "impl", "file.c")
    assert result == "src/core/impl/file.c"


def test_join_paths_empty_parts():
    """Test joining with empty parts."""
    result = join_paths("src", "", "include")
    assert result == "src/include"


def test_join_paths_normalizes():
    """Test that joined paths are normalized."""
    result = join_paths("src\\", "include")
    assert result == "src/include"
    assert "\\" not in result


def test_join_paths_all_empty():
    """Test joining all empty parts."""
    result = join_paths("", "", "")
    assert result == ""


def test_join_paths_invalid_raises():
    """Test that invalid parts raise ValueError."""
    with pytest.raises(ValueError):
        join_paths("src", "../invalid")


def test_validate_paths_empty_allowed():
    """Test validating paths with empty allowed."""
    paths = ["", "src/"]
    result = validate_paths(paths, allow_empty=True)
    assert "src" in result
