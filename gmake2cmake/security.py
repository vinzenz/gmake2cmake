"""Security hardening for path operations and file access.

Provides sandbox validation, path traversal prevention, and resource limits
for secure handling of file operations and user inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

# Maximum file size for parsing (100MB)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

# Allowed file extensions for Makefiles and includes
ALLOWED_EXTENSIONS = {
    ".mk",           # Makefile fragments
    ".make",         # Makefile variants
    "",              # No extension (typical for Makefile)
    ".gmk",          # GNU Makefile
    ".h",            # Header files that might be included
    ".c", ".cc", ".cpp", ".cxx",  # C/C++ source
    ".h", ".hpp", ".hxx",         # C/C++ headers
    ".txt",          # Documentation
}


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class PathTraversalError(SecurityError):
    """Raised when a path traversal attack is detected."""
    pass


class SandboxViolationError(SecurityError):
    """Raised when an operation violates sandbox boundaries."""
    pass


class ResourceExhaustionError(SecurityError):
    """Raised when resource limits are exceeded."""
    pass


def validate_path_in_sandbox(
    path: Path,
    sandbox_root: Path
) -> Path:
    """Validate that a path is within the sandbox root.

    Prevents directory traversal attacks by ensuring resolved absolute path
    is within or equal to the sandbox root.

    Args:
        path: Path to validate (can be relative or absolute)
        sandbox_root: Root directory that constrains operations

    Returns:
        Resolved absolute Path

    Raises:
        PathTraversalError: If path escapes sandbox_root
        SandboxViolationError: If symlink points outside sandbox
    """
    # Resolve both paths to absolute form, following symlinks
    resolved = path.resolve()
    root = sandbox_root.resolve()

    # Check if resolved path is within sandbox
    try:
        resolved.relative_to(root)
    except ValueError as e:
        raise PathTraversalError(
            f"Path traversal detected: {path} resolves to {resolved} "
            f"which is outside sandbox {root}"
        ) from e

    return resolved


def validate_symlink_target(
    symlink_path: Path,
    sandbox_root: Path
) -> Path:
    """Validate that a symlink target is within the sandbox.

    Prevents symlink attacks by following symlinks and verifying targets
    are within the sandbox.

    Args:
        symlink_path: Path to the symlink itself
        sandbox_root: Root directory that constrains operations

    Returns:
        Resolved target path

    Raises:
        SandboxViolationError: If symlink target is outside sandbox
    """
    if not symlink_path.is_symlink():
        return symlink_path.resolve()

    # Resolve the symlink target
    target = symlink_path.resolve()

    # Ensure target is in sandbox
    try:
        target.relative_to(sandbox_root.resolve())
    except ValueError as e:
        raise SandboxViolationError(
            f"Symlink {symlink_path} points outside sandbox to {target}"
        ) from e

    return target


def validate_file_size(
    path: Path,
    max_bytes: int = MAX_FILE_SIZE_BYTES
) -> int:
    """Validate that a file does not exceed size limits.

    Prevents resource exhaustion attacks by rejecting overly large files.

    Args:
        path: Path to file to check
        max_bytes: Maximum allowed size in bytes

    Returns:
        File size in bytes

    Raises:
        ResourceExhaustionError: If file exceeds max_bytes
        FileNotFoundError: If file does not exist
    """
    try:
        size = path.stat().st_size
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e

    if size > max_bytes:
        raise ResourceExhaustionError(
            f"File {path} size {size} bytes exceeds limit {max_bytes} bytes"
        )

    return size


def validate_file_extension(
    path: Path,
    allowed: Optional[Set[str]] = None
) -> str:
    """Validate that a file has an allowed extension.

    Restricts file types to prevent processing of unexpected file formats.

    Args:
        path: Path to file to check
        allowed: Set of allowed extensions (with dots), defaults to ALLOWED_EXTENSIONS

    Returns:
        The file extension

    Raises:
        SecurityError: If extension is not in allowed list
    """
    if allowed is None:
        allowed = ALLOWED_EXTENSIONS

    suffix = path.suffix.lower()
    if suffix not in allowed:
        raise SecurityError(
            f"File extension {suffix} not in allowed list: {allowed}"
        )

    return suffix


def create_sandbox(
    root_path: Path,
    must_exist: bool = True
) -> Path:
    """Create or validate a sandbox directory for file operations.

    Args:
        root_path: Path to sandbox root directory
        must_exist: If True, directory must exist; if False, will be created

    Returns:
        Resolved absolute path to sandbox root

    Raises:
        FileNotFoundError: If must_exist=True and directory doesn't exist
        OSError: If unable to create or access directory
    """
    resolved = root_path.resolve()

    if must_exist:
        if not resolved.is_dir():
            raise FileNotFoundError(f"Sandbox root not found: {resolved}")
    else:
        resolved.mkdir(parents=True, exist_ok=True)

    return resolved


def sanitize_command_arg(arg: str) -> str:
    """Sanitize command-line arguments to prevent injection.

    Validates that command arguments don't contain shell metacharacters
    that could be exploited for command injection.

    Args:
        arg: Command argument to sanitize

    Returns:
        Validated argument

    Raises:
        SecurityError: If argument contains suspicious characters
    """
    # Characters that are dangerous in shell contexts
    dangerous_chars = {'|', '&', ';', '`', '$', '\n', '\r', '(', ')', '<', '>'}

    if any(char in arg for char in dangerous_chars):
        raise SecurityError(
            f"Command argument contains shell metacharacters: {arg!r}"
        )

    return arg


def validate_identifier(name: str, max_length: int = 256) -> str:
    """Validate that a name is a valid identifier.

    Restricts identifiers to alphanumeric, underscore, and hyphen characters
    to prevent injection through names.

    Args:
        name: Identifier to validate
        max_length: Maximum allowed length

    Returns:
        Validated identifier

    Raises:
        SecurityError: If identifier is invalid
    """
    if not name:
        raise SecurityError("Identifier cannot be empty")

    if len(name) > max_length:
        raise SecurityError(
            f"Identifier exceeds maximum length {max_length}: {name!r}"
        )

    # Allow alphanumeric, underscore, hyphen, dot
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    if not all(c in allowed_chars for c in name):
        raise SecurityError(
            f"Identifier contains invalid characters: {name!r}. "
            f"Only alphanumeric, underscore, hyphen, and dot allowed."
        )

    return name
