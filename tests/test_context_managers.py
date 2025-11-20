"""Tests for context managers in fs module."""

from __future__ import annotations

from gmake2cmake.fs import atomic_write, temporary_directory


def test_atomic_write_success(tmp_path):
    """Test atomic write succeeds and file is created."""
    target = tmp_path / "output.txt"

    with atomic_write(target) as tmp:
        tmp.write_text("test content")

    assert target.exists()
    assert target.read_text() == "test content"


def test_atomic_write_failure_no_file(tmp_path):
    """Test that file is not created if context fails."""
    target = tmp_path / "output.txt"

    try:
        with atomic_write(target) as tmp:
            tmp.write_text("partial content")
            raise ValueError("simulated error")
    except ValueError:
        pass

    assert not target.exists()


def test_atomic_write_overwrites_existing(tmp_path):
    """Test atomic write overwrites existing file."""
    target = tmp_path / "output.txt"
    target.write_text("old content")

    with atomic_write(target) as tmp:
        tmp.write_text("new content")

    assert target.read_text() == "new content"


def test_atomic_write_creates_parents(tmp_path):
    """Test atomic write creates parent directories."""
    target = tmp_path / "subdir1" / "subdir2" / "output.txt"

    with atomic_write(target) as tmp:
        tmp.write_text("nested content")

    assert target.exists()
    assert target.read_text() == "nested content"


def test_atomic_write_temp_file_cleaned_on_error(tmp_path):
    """Test that temporary file is cleaned up on error."""
    target = tmp_path / "output.txt"
    temp_files_before = set(tmp_path.glob(".tmp_*"))

    try:
        with atomic_write(target) as tmp:
            # Verify temp file exists during context
            assert tmp.exists()
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass

    # Temp file should be cleaned up
    temp_files_after = set(tmp_path.glob(".tmp_*"))
    assert len(temp_files_after) == len(temp_files_before)


def test_temporary_directory_created():
    """Test that temporary directory is created."""
    with temporary_directory() as tmpdir:
        assert tmpdir.exists()
        assert tmpdir.is_dir()


def test_temporary_directory_usable():
    """Test that temporary directory can be used for file operations."""
    with temporary_directory() as tmpdir:
        test_file = tmpdir / "test.txt"
        test_file.write_text("test data")
        assert test_file.read_text() == "test data"


def test_temporary_directory_cleaned_on_success():
    """Test that temporary directory is cleaned up after success."""
    tmpdir_path = None
    with temporary_directory() as tmpdir:
        tmpdir_path = tmpdir
        # Create files in it
        (tmpdir / "file1.txt").write_text("content1")
        (tmpdir / "subdir").mkdir()
        (tmpdir / "subdir" / "file2.txt").write_text("content2")

    # Directory should be cleaned up
    assert not tmpdir_path.exists()


def test_temporary_directory_cleaned_on_error():
    """Test that temporary directory is cleaned up even on error."""
    tmpdir_path = None
    try:
        with temporary_directory() as tmpdir:
            tmpdir_path = tmpdir
            (tmpdir / "file.txt").write_text("content")
            raise ValueError("simulated error")
    except ValueError:
        pass

    # Directory should still be cleaned up
    assert not tmpdir_path.exists()


def test_temporary_directory_creates_nested_files():
    """Test that nested file structures work correctly."""
    with temporary_directory() as tmpdir:
        nested = tmpdir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        test_file = nested / "deep.txt"
        test_file.write_text("deeply nested")

        assert test_file.read_text() == "deeply nested"
