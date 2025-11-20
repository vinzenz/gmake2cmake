"""Path validation and normalization utilities."""

from __future__ import annotations

from typing import List


def validate_path(path: str, allow_empty: bool = False, allow_traversal: bool = False) -> str:
    """Validate and normalize a single path.

    Args:
        path: Path string to validate.
        allow_empty: If True, allow empty strings.
        allow_traversal: If True, allow '..' in paths.

    Returns:
        Normalized path.

    Raises:
        ValueError: If path is invalid.
    """
    if not path or not path.strip():
        if allow_empty:
            return ""
        raise ValueError("Path cannot be empty")

    # Check for traversal
    if not allow_traversal and ".." in path:
        raise ValueError(f"Path traversal (..) not allowed: {path}")

    # Normalize separators
    normalized = path.replace("\\", "/").rstrip("/")

    # Check for null bytes
    if "\x00" in normalized:
        raise ValueError("Null bytes not allowed in paths")

    return normalized


def validate_paths(paths: List[str], allow_empty: bool = False, allow_traversal: bool = False) -> List[str]:
    """Validate and normalize a list of paths.

    Args:
        paths: List of path strings.
        allow_empty: If True, allow empty strings.
        allow_traversal: If True, allow '..' in paths.

    Returns:
        List of validated and normalized paths without duplicates.

    Raises:
        ValueError: If any path is invalid.
    """
    seen = set()
    validated = []

    for path in paths:
        normalized = validate_path(path, allow_empty, allow_traversal)
        if not normalized and not allow_empty:
            continue
        if normalized and normalized not in seen:
            seen.add(normalized)
            validated.append(normalized)

    return validated


def is_valid_path(path: str) -> bool:
    """Check if a path is valid without raising errors.

    Args:
        path: Path string to check.

    Returns:
        True if path is valid, False otherwise.
    """
    try:
        validate_path(path)
        return True
    except ValueError:
        return False


def normalize_glob_pattern(pattern: str) -> str:
    """Normalize a glob pattern for path matching.

    Args:
        pattern: Glob pattern string.

    Returns:
        Normalized pattern.

    Raises:
        ValueError: If pattern is invalid.
    """
    if not pattern or not pattern.strip():
        raise ValueError("Pattern cannot be empty")

    # Normalize separators
    normalized = pattern.replace("\\", "/")

    # Validate no null bytes
    if "\x00" in normalized:
        raise ValueError("Null bytes not allowed in patterns")

    return normalized


def is_path_absolute(path: str) -> bool:
    """Check if a path is absolute.

    Args:
        path: Path string to check.

    Returns:
        True if path is absolute, False otherwise.
    """
    normalized = path.replace("\\", "/")
    return normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":")


def join_paths(*parts: str) -> str:
    """Join path parts safely.

    Args:
        *parts: Path parts to join.

    Returns:
        Joined path in posix format.

    Raises:
        ValueError: If any part is invalid.
    """
    validated_parts = [validate_path(p, allow_empty=True) for p in parts]
    # Filter out empty parts
    non_empty = [p for p in validated_parts if p]
    if not non_empty:
        return ""
    return "/".join(non_empty)
