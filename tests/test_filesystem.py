"""Tests for filesystem adapters."""

import tempfile
from pathlib import Path

import pytest

from gmake2cmake.fs import LocalFS, TestFileSystemAdapter


class TestLocalFS:
    """Tests for LocalFS adapter with real filesystem."""

    def test_read_text(self):
        """Test reading text file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("hello world")
            f.flush()
            path = Path(f.name)

        try:
            fs = LocalFS()
            content = fs.read_text(path)
            assert content == "hello world"
        finally:
            path.unlink()

    def test_write_text(self):
        """Test writing text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "test.txt"
            fs = LocalFS()
            fs.write_text(path, "test content")
            assert path.exists()
            assert path.read_text() == "test content"

    def test_read_file_bytes(self):
        """Test reading file as bytes."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"\x00\x01\x02")
            f.flush()
            path = Path(f.name)

        try:
            fs = LocalFS()
            content = fs.read_file(path)
            assert content == b"\x00\x01\x02"
        finally:
            path.unlink()

    def test_write_file_bytes(self):
        """Test writing file as bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "binary.bin"
            fs = LocalFS()
            fs.write_file(path, b"\x00\x01\x02")
            assert path.exists()
            assert path.read_bytes() == b"\x00\x01\x02"

    def test_exists(self):
        """Test file existence check."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)

        try:
            fs = LocalFS()
            assert fs.exists(path)
            path.unlink()
            assert not fs.exists(path)
        finally:
            if path.exists():
                path.unlink()

    def test_is_file(self):
        """Test file type check."""
        with tempfile.NamedTemporaryFile() as f:
            path = Path(f.name)
            fs = LocalFS()
            assert fs.is_file(path)

    def test_is_dir(self):
        """Test directory type check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            fs = LocalFS()
            assert fs.is_dir(path)

    def test_makedirs(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "a" / "b" / "c"
            fs = LocalFS()
            fs.makedirs(path)
            assert path.is_dir()

    def test_makedirs_idempotent(self):
        """Test makedirs doesn't fail when dir exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test"
            fs = LocalFS()
            fs.makedirs(path)
            fs.makedirs(path)  # Should not raise
            assert path.is_dir()

    def test_list_dir(self):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "b.txt").write_text("b")
            (base / "a.txt").write_text("a")
            (base / "c.txt").write_text("c")

            fs = LocalFS()
            entries = fs.list_dir(base)
            names = [p.name for p in entries]
            assert names == ["a.txt", "b.txt", "c.txt"]  # Sorted

    def test_resolve_path(self):
        """Test path resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("test")
            fs = LocalFS()
            resolved = fs.resolve_path(path)
            assert resolved.is_absolute()
            assert resolved.exists()

    def test_normalize_path(self):
        """Test path normalization to POSIX."""
        fs = LocalFS()
        path = Path("some/test/path.txt")
        normalized = fs.normalize_path(path)
        assert normalized == "some/test/path.txt"
        assert "/" in normalized

    def test_get_mtime(self):
        """Test getting file modification time."""
        with tempfile.NamedTemporaryFile() as f:
            path = Path(f.name)
            fs = LocalFS()
            mtime = fs.get_mtime(path)
            assert mtime > 0
            assert isinstance(mtime, float)


class TestTestFileSystemAdapter:
    """Tests for TestFileSystemAdapter virtual filesystem."""

    def test_read_write_text(self):
        """Test reading and writing text."""
        fs = TestFileSystemAdapter()
        path = Path("test.txt")
        fs.write_text(path, "hello")
        assert fs.read_text(path) == "hello"

    def test_read_nonexistent_raises(self):
        """Test reading nonexistent file raises error."""
        fs = TestFileSystemAdapter()
        path = Path("missing.txt")
        with pytest.raises(FileNotFoundError):
            fs.read_text(path)

    def test_read_file_bytes(self):
        """Test reading file as bytes."""
        fs = TestFileSystemAdapter()
        path = Path("binary.bin")
        fs.write_text(path, "hello")
        assert fs.read_file(path) == b"hello"

    def test_write_file_bytes(self):
        """Test writing file as bytes."""
        fs = TestFileSystemAdapter()
        path = Path("binary.bin")
        fs.write_file(path, b"hello")
        assert fs.read_text(path) == "hello"

    def test_exists(self):
        """Test file existence check."""
        fs = TestFileSystemAdapter()
        path = Path("test.txt")
        assert not fs.exists(path)
        fs.write_text(path, "content")
        assert fs.exists(path)

    def test_is_file(self):
        """Test file type check."""
        fs = TestFileSystemAdapter()
        path = Path("test.txt")
        fs.write_text(path, "content")
        assert fs.is_file(path)
        assert not fs.is_file(Path("missing.txt"))

    def test_is_dir(self):
        """Test directory type check."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("dir/test.txt"), "content")
        assert fs.is_dir(Path("dir"))
        assert not fs.is_dir(Path("dir/test.txt"))
        assert not fs.is_dir(Path("nonexistent"))

    def test_makedirs_noop(self):
        """Test makedirs is no-op for virtual fs."""
        fs = TestFileSystemAdapter()
        fs.makedirs(Path("a/b/c"))  # Should not raise

    def test_list_dir(self):
        """Test listing directory contents."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("dir/b.txt"), "b")
        fs.write_text(Path("dir/a.txt"), "a")
        fs.write_text(Path("dir/c.txt"), "c")
        fs.write_text(Path("dir/sub/file.txt"), "sub")

        entries = fs.list_dir(Path("dir"))
        names = [p.name for p in entries]
        assert names == ["a.txt", "b.txt", "c.txt", "sub"]  # Sorted

    def test_normalize_path(self):
        """Test path normalization."""
        fs = TestFileSystemAdapter()
        path = Path("some/test/path.txt")
        normalized = fs.normalize_path(path)
        assert normalized == "some/test/path.txt"

    def test_get_mtime_deterministic(self):
        """Test deterministic mtime assignment."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("a.txt"), "a")
        fs.write_text(Path("b.txt"), "b")
        fs.write_text(Path("c.txt"), "c")

        mtime_a = fs.get_mtime(Path("a.txt"))
        mtime_b = fs.get_mtime(Path("b.txt"))
        mtime_c = fs.get_mtime(Path("c.txt"))

        assert mtime_a == 1000.0
        assert mtime_b == 1001.0
        assert mtime_c == 1002.0

    def test_get_mtime_nonexistent_raises(self):
        """Test get_mtime raises for missing file."""
        fs = TestFileSystemAdapter()
        with pytest.raises(FileNotFoundError):
            fs.get_mtime(Path("missing.txt"))

    def test_resolve_path(self):
        """Test path resolution."""
        fs = TestFileSystemAdapter()
        path = Path("test.txt")
        resolved = fs.resolve_path(path)
        assert isinstance(resolved, Path)

    def test_overwrite_preserves_mtime(self):
        """Test that overwriting a file preserves its mtime."""
        fs = TestFileSystemAdapter()
        path = Path("test.txt")
        fs.write_text(path, "original")
        mtime1 = fs.get_mtime(path)
        fs.write_text(path, "modified")
        mtime2 = fs.get_mtime(path)
        assert mtime1 == mtime2

    def test_nested_paths(self):
        """Test handling of nested paths."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("a/b/c/file.txt"), "deep")
        assert fs.exists(Path("a/b/c/file.txt"))
        assert fs.is_file(Path("a/b/c/file.txt"))
        assert fs.is_dir(Path("a"))
        assert fs.is_dir(Path("a/b"))
        assert fs.is_dir(Path("a/b/c"))

    def test_list_dir_with_nesting(self):
        """Test list_dir with nested structure."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("root/file1.txt"), "1")
        fs.write_text(Path("root/file2.txt"), "2")
        fs.write_text(Path("root/subdir/file3.txt"), "3")
        fs.write_text(Path("root/subdir/nested/file4.txt"), "4")

        entries = fs.list_dir(Path("root"))
        names = sorted([p.name for p in entries])
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names
        assert len(names) == 3  # file1, file2, subdir

    def test_path_with_trailing_slash(self):
        """Test handling paths with trailing slashes."""
        fs = TestFileSystemAdapter()
        fs.write_text(Path("dir/file.txt"), "content")
        assert fs.is_dir(Path("dir"))
        assert fs.is_dir(Path("dir/"))


class TestLocalFSErrorHandling:
    """Tests for LocalFS error handling and recovery."""

    def test_read_text_missing_file_raises(self):
        """Test reading missing file raises FileNotFoundError with path info."""
        fs = LocalFS()
        missing = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError) as exc_info:
            fs.read_text(missing)
        assert "not found" in str(exc_info.value).lower()
        assert str(missing) in str(exc_info.value)

    def test_read_text_permission_denied_raises(self):
        """Test reading file without permission raises PermissionError with path info."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)
            f.write(b"content")

        try:
            # Remove read permission
            path.chmod(0o000)
            fs = LocalFS()
            with pytest.raises(PermissionError) as exc_info:
                fs.read_text(path)
            assert "permission" in str(exc_info.value).lower()
            assert str(path) in str(exc_info.value)
        finally:
            # Restore permission for cleanup
            path.chmod(0o644)
            path.unlink()

    def test_read_text_unicode_error(self):
        """Test reading file with invalid UTF-8 raises UnicodeDecodeError."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Write invalid UTF-8 sequence
            f.write(b"\x80\x81\x82")
            path = Path(f.name)

        try:
            fs = LocalFS()
            with pytest.raises(UnicodeDecodeError) as exc_info:
                fs.read_text(path)
            assert "utf-8" in str(exc_info.value).lower()
            assert str(path) in str(exc_info.value)
        finally:
            path.unlink()

    def test_write_text_permission_denied_raises(self):
        """Test writing to read-only directory raises PermissionError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            readonly_dir = Path(tmpdir) / "readonly"
            readonly_dir.mkdir()
            target = readonly_dir / "file.txt"

            try:
                readonly_dir.chmod(0o444)  # Read-only
                fs = LocalFS()
                with pytest.raises(PermissionError) as exc_info:
                    fs.write_text(target, "content")
                assert "permission" in str(exc_info.value).lower()
                assert str(target) in str(exc_info.value)
            finally:
                readonly_dir.chmod(0o755)

    def test_list_dir_missing_directory_raises(self):
        """Test listing missing directory raises FileNotFoundError."""
        fs = LocalFS()
        missing = Path("/nonexistent/directory")
        with pytest.raises(FileNotFoundError) as exc_info:
            fs.list_dir(missing)
        assert "not found" in str(exc_info.value).lower()

    def test_list_dir_not_a_directory_raises(self):
        """Test listing non-directory raises NotADirectoryError."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)

        try:
            fs = LocalFS()
            with pytest.raises(NotADirectoryError) as exc_info:
                fs.list_dir(path)
            assert "not a directory" in str(exc_info.value).lower()
        finally:
            path.unlink()

    def test_get_mtime_missing_file_raises(self):
        """Test getting mtime of missing file raises FileNotFoundError."""
        fs = LocalFS()
        missing = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError) as exc_info:
            fs.get_mtime(missing)
        assert "not found" in str(exc_info.value).lower()

    def test_makedirs_with_permission_denied(self):
        """Test makedirs with permission denied raises PermissionError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir) / "parent"
            parent.mkdir()
            subdir = parent / "subdir"

            try:
                parent.chmod(0o444)  # Read-only
                fs = LocalFS()
                with pytest.raises(PermissionError) as exc_info:
                    fs.makedirs(subdir)
                assert "permission" in str(exc_info.value).lower()
            finally:
                parent.chmod(0o755)

    def test_safe_read_text_missing_file_returns_default(self):
        """Test safe_read_text returns default for missing file."""
        fs = LocalFS()
        result = fs.safe_read_text(Path("/nonexistent/file.txt"), default="fallback")
        assert result == "fallback"

    def test_safe_read_text_missing_file_returns_empty_by_default(self):
        """Test safe_read_text returns empty string by default for missing file."""
        fs = LocalFS()
        result = fs.safe_read_text(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_safe_read_text_existing_file_returns_content(self):
        """Test safe_read_text returns actual content for existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            path = Path(f.name)

        try:
            fs = LocalFS()
            result = fs.safe_read_text(path)
            assert result == "test content"
        finally:
            path.unlink()

    def test_safe_read_text_permission_denied_returns_default(self):
        """Test safe_read_text returns default even with permission error."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content")
            path = Path(f.name)

        try:
            path.chmod(0o000)
            fs = LocalFS()
            result = fs.safe_read_text(path, default="fallback")
            assert result == "fallback"
        finally:
            path.chmod(0o644)
            path.unlink()

    def test_can_write_valid_directory(self):
        """Test can_write returns True for writable directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.txt"
            fs = LocalFS()
            assert fs.can_write(path) is True

    def test_can_write_readonly_directory(self):
        """Test can_write returns False for read-only directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            readonly_dir = Path(tmpdir) / "readonly"
            readonly_dir.mkdir()
            path = readonly_dir / "file.txt"

            try:
                readonly_dir.chmod(0o444)
                fs = LocalFS()
                assert fs.can_write(path) is False
            finally:
                readonly_dir.chmod(0o755)

    def test_can_write_nonexistent_parent(self):
        """Test can_write returns False for nonexistent parent directory."""
        path = Path("/nonexistent/deep/path/file.txt")
        fs = LocalFS()
        assert fs.can_write(path) is False

    def test_can_write_file_not_directory(self):
        """Test can_write returns False when parent is a file, not directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)

        try:
            # Try to create file under a file (path is file, not directory)
            invalid_parent = path / "nested" / "file.txt"
            fs = LocalFS()
            assert fs.can_write(invalid_parent) is False
        finally:
            path.unlink()

    def test_error_messages_contain_path(self):
        """Test that error messages include the problematic path."""
        fs = LocalFS()
        test_path = Path("/nonexistent/test/path.txt")

        with pytest.raises(FileNotFoundError) as exc_info:
            fs.read_text(test_path)

        error_msg = str(exc_info.value)
        assert str(test_path) in error_msg
        assert "not found" in error_msg.lower()

    def test_error_chain_preserves_original(self):
        """Test that error chaining preserves original exception."""
        fs = LocalFS()
        test_path = Path("/nonexistent/file.txt")

        try:
            fs.read_text(test_path)
        except FileNotFoundError as e:
            # Check that __cause__ is set (error chaining with 'from')
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, FileNotFoundError)
