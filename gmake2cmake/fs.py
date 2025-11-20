from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Generator, List, Protocol


class FileSystemAdapter(Protocol):
    """Abstract interface for filesystem operations enabling dependency injection and testing.

    All read/write methods may raise OSError and subclasses (FileNotFoundError, PermissionError, etc).
    Methods that access filesystem metadata (exists, is_file, is_dir, list_dir, get_mtime) should
    handle missing paths gracefully or raise FileNotFoundError.
    """

    def read_text(self, path: Path) -> str:
        """Read file contents as UTF-8 text.

        Args:
            path: Path to file to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If lacking read permission
            UnicodeDecodeError: If file is not valid UTF-8
            OSError: For other IO errors (disk read failure, etc)
        """
        ...

    def write_text(self, path: Path, data: str) -> None:
        """Write text contents to file (creates parent dirs, UTF-8 encoding).

        Args:
            path: Path to file to write (parent directories created if needed)
            data: Content to write as string

        Returns:
            None

        Raises:
            PermissionError: If lacking write permission
            OSError: For other IO errors (disk full, invalid path, etc)
        """
        ...

    def read_file(self, path: Path) -> bytes:
        """Read file contents as raw bytes.

        Args:
            path: Path to file to read

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If lacking read permission
            OSError: For other IO errors
        """
        ...

    def write_file(self, path: Path, data: bytes) -> None:
        """Write raw bytes to file (creates parent dirs).

        Args:
            path: Path to file to write (parent directories created if needed)
            data: Content to write as bytes

        Returns:
            None

        Raises:
            PermissionError: If lacking write permission
            OSError: For other IO errors
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if path exists (file or directory).

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise (never raises for nonexistent paths)

        Raises:
            OSError: For permission errors or other IO issues
        """
        ...

    def is_file(self, path: Path) -> bool:
        """Check if path is a regular file.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a regular file, False otherwise

        Raises:
            OSError: For permission errors or other IO issues
        """
        ...

    def is_dir(self, path: Path) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a directory, False otherwise

        Raises:
            OSError: For permission errors or other IO issues
        """
        ...

    def makedirs(self, path: Path) -> None:
        """Create directory and parent directories (no-op if exists).

        Args:
            path: Directory path to create

        Returns:
            None (idempotent - no error if directory already exists)

        Raises:
            PermissionError: If lacking write permission to parent
            OSError: For other IO errors
        """
        ...

    def list_dir(self, path: Path) -> List[Path]:
        """List directory contents, sorted deterministically.

        Args:
            path: Directory path to list

        Returns:
            Sorted list of Path objects (immediate children only)

        Raises:
            FileNotFoundError: If directory does not exist
            PermissionError: If lacking read permission
            NotADirectoryError: If path exists but is not a directory
            OSError: For other IO errors
        """
        ...

    def resolve_path(self, path: Path) -> Path:
        """Resolve path to absolute form (follows symlinks).

        Args:
            path: Path to resolve

        Returns:
            Absolute resolved Path

        Raises:
            OSError: For permission errors accessing symlink targets
        """
        ...

    def normalize_path(self, path: Path) -> str:
        """Normalize path to POSIX-style string.

        Args:
            path: Path to normalize

        Returns:
            Path as POSIX string (forward slashes, no trailing slash)

        Raises:
            None (purely computational)
        """
        ...

    def get_mtime(self, path: Path) -> float:
        """Get file modification time as float (seconds since epoch).

        Args:
            path: Path to file

        Returns:
            Modification time as float seconds since epoch

        Raises:
            FileNotFoundError: If path does not exist
            OSError: For permission errors or other IO errors
        """
        ...


@dataclass
class LocalFS:
    """Real filesystem adapter using pathlib for local filesystem operations.

    Wraps OS-level I/O operations with informative error messages while preserving
    specific exception types (FileNotFoundError, PermissionError, etc) for caller handling.
    """

    def read_text(self, path: Path) -> str:
        """Read file contents as UTF-8 text.

        Args:
            path: Path to file to read

        Returns:
            File contents as UTF-8 string

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If lacking read permission
            UnicodeDecodeError: If file is not valid UTF-8
            OSError: For other IO errors with path context
        """
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Cannot read file (not found): {path}") from e
        except PermissionError as e:
            raise PermissionError(f"Cannot read file (permission denied): {path}") from e
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding,
                e.object,
                e.start,
                e.end,
                f"File is not valid UTF-8: {path}"
            ) from e
        except OSError as e:
            raise OSError(f"Error reading file {path}: {e}") from e

    def write_text(self, path: Path, data: str) -> None:
        """Write text contents to file with UTF-8 encoding.

        Args:
            path: Path to file to write (parent directories created if needed)
            data: Content to write as string

        Returns:
            None

        Raises:
            PermissionError: If lacking write permission
            OSError: For other IO errors with path context
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        except PermissionError as e:
            raise PermissionError(f"Cannot write file (permission denied): {path}") from e
        except OSError as e:
            raise OSError(f"Error writing file {path}: {e}") from e

    def read_file(self, path: Path) -> bytes:
        """Read file contents as raw bytes.

        Args:
            path: Path to file to read

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If lacking read permission
            OSError: For other IO errors
        """
        try:
            return path.read_bytes()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Cannot read file (not found): {path}") from e
        except PermissionError as e:
            raise PermissionError(f"Cannot read file (permission denied): {path}") from e
        except OSError as e:
            raise OSError(f"Error reading file {path}: {e}") from e

    def write_file(self, path: Path, data: bytes) -> None:
        """Write raw bytes to file.

        Args:
            path: Path to file to write (parent directories created if needed)
            data: Content to write as bytes

        Returns:
            None

        Raises:
            PermissionError: If lacking write permission
            OSError: For other IO errors
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except PermissionError as e:
            raise PermissionError(f"Cannot write file (permission denied): {path}") from e
        except OSError as e:
            raise OSError(f"Error writing file {path}: {e}") from e

    def exists(self, path: Path) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise

        Raises:
            OSError: For permission errors or broken symlinks
        """
        try:
            return path.exists()
        except OSError as e:
            raise OSError(f"Error checking path existence {path}: {e}") from e

    def is_file(self, path: Path) -> bool:
        """Check if path is a regular file.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a regular file, False otherwise

        Raises:
            OSError: For permission errors
        """
        try:
            return path.is_file()
        except OSError as e:
            raise OSError(f"Error checking if file {path}: {e}") from e

    def is_dir(self, path: Path) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a directory, False otherwise

        Raises:
            OSError: For permission errors
        """
        try:
            return path.is_dir()
        except OSError as e:
            raise OSError(f"Error checking if directory {path}: {e}") from e

    def makedirs(self, path: Path) -> None:
        """Create directory and parent directories.

        Args:
            path: Directory path to create

        Returns:
            None (idempotent)

        Raises:
            PermissionError: If lacking write permission to parent
            OSError: For other IO errors
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create directory (permission denied): {path}") from e
        except OSError as e:
            raise OSError(f"Error creating directory {path}: {e}") from e

    def list_dir(self, path: Path) -> List[Path]:
        """List directory contents, sorted for deterministic ordering.

        Args:
            path: Directory path to list

        Returns:
            Sorted list of Path objects (immediate children only)

        Raises:
            FileNotFoundError: If directory does not exist
            PermissionError: If lacking read permission
            NotADirectoryError: If path exists but is not a directory
            OSError: For other IO errors
        """
        try:
            entries = list(path.iterdir())
            return sorted(entries)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Cannot list directory (not found): {path}") from e
        except PermissionError as e:
            raise PermissionError(f"Cannot list directory (permission denied): {path}") from e
        except NotADirectoryError as e:
            raise NotADirectoryError(f"Path is not a directory: {path}") from e
        except OSError as e:
            raise OSError(f"Error listing directory {path}: {e}") from e

    def resolve_path(self, path: Path) -> Path:
        """Resolve path to absolute form following symlinks.

        Args:
            path: Path to resolve

        Returns:
            Absolute resolved Path

        Raises:
            OSError: For permission errors accessing symlink targets
        """
        try:
            return path.resolve()
        except OSError as e:
            raise OSError(f"Error resolving path {path}: {e}") from e

    def normalize_path(self, path: Path) -> str:
        """Normalize path to POSIX-style string.

        Args:
            path: Path to normalize

        Returns:
            Path as POSIX string (forward slashes)

        Raises:
            None (purely computational)
        """
        return path.as_posix()

    def get_mtime(self, path: Path) -> float:
        """Get file modification time as float (seconds since epoch).

        Args:
            path: Path to file

        Returns:
            Modification time as float seconds since epoch

        Raises:
            FileNotFoundError: If path does not exist
            OSError: For permission errors or other IO errors
        """
        try:
            return path.stat().st_mtime
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Cannot get mtime (file not found): {path}") from e
        except OSError as e:
            raise OSError(f"Error getting mtime for {path}: {e}") from e

    def safe_read_text(self, path: Path, default: str = "") -> str:
        """Safely read file contents, returning default if file not found or unreadable.

        This is a convenience helper for optional file reads where missing files
        are not an error condition.

        Args:
            path: Path to file to read
            default: Value to return if file cannot be read (default: empty string)

        Returns:
            File contents as UTF-8 string, or default value if read fails

        Raises:
            None (all errors are caught and default is returned)
        """
        try:
            return self.read_text(path)
        except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
            return default

    def can_write(self, path: Path) -> bool:
        """Check if a file can be written (parent directory exists and is writable).

        This is a convenience helper for checking write permissions before attempting
        to write. Note that this is not atomic - permission may change between check
        and actual write.

        Args:
            path: Path to file to check write capability

        Returns:
            True if parent directory exists and appears writable, False otherwise

        Raises:
            None (all errors return False)
        """
        try:
            parent = path.parent
            return self.is_dir(parent) and bool(parent.stat().st_mode & 0o200)
        except (OSError, FileNotFoundError):
            return False


@dataclass
class TestFileSystemAdapter:
    """In-memory virtual filesystem for unit testing with deterministic behavior."""

    __test__ = False  # prevent pytest from collecting this helper as a test class

    files: Dict[str, str] = field(default_factory=dict)
    """Mapping of normalized paths to file contents."""

    mtimes: Dict[str, float] = field(default_factory=dict)
    """Mapping of normalized paths to modification times."""

    _next_mtime: float = field(default=1000.0, init=False)
    """Counter for deterministic mtime assignments."""

    def _normalize(self, path: Path) -> str:
        """Normalize path to POSIX form for internal storage."""
        return path.as_posix()

    def read_text(self, path: Path) -> str:
        """Read file contents as UTF-8 text."""
        normalized = self._normalize(path)
        if normalized not in self.files:
            raise FileNotFoundError(f"{path}")
        return self.files[normalized]

    def write_text(self, path: Path, data: str) -> None:
        """Write text contents to file."""
        normalized = self._normalize(path)
        self.files[normalized] = data
        if normalized not in self.mtimes:
            self.mtimes[normalized] = self._next_mtime
            self._next_mtime += 1.0

    def read_file(self, path: Path) -> bytes:
        """Read file contents as raw bytes."""
        return self.read_text(path).encode("utf-8")

    def write_file(self, path: Path, data: bytes) -> None:
        """Write raw bytes to file."""
        self.write_text(path, data.decode("utf-8"))

    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        normalized = self._normalize(path)
        return normalized in self.files

    def is_file(self, path: Path) -> bool:
        """Check if path is a regular file."""
        return self.exists(path)

    def is_dir(self, path: Path) -> bool:
        """Check if path is a directory (always False for virtual fs)."""
        normalized = self._normalize(path)
        # Check if any file starts with this path as directory
        dir_prefix = normalized if normalized.endswith("/") else normalized + "/"
        return any(f.startswith(dir_prefix) for f in self.files)

    def makedirs(self, path: Path) -> None:
        """Create directory (no-op for virtual fs)."""
        pass

    def list_dir(self, path: Path) -> List[Path]:
        """List directory contents, sorted deterministically."""
        normalized = self._normalize(path)
        dir_prefix = normalized if normalized.endswith("/") else normalized + "/"

        # Find all immediate children
        children_names = set()
        for file_path in self.files:
            if file_path.startswith(dir_prefix):
                # Get the part after the directory prefix
                relative = file_path[len(dir_prefix):]
                # Take only the first path component (immediate child)
                child_name = relative.split("/")[0]
                if child_name:
                    children_names.add(child_name)

        # Return sorted Path objects
        result = [Path(normalized) / child for child in sorted(children_names)]
        return result

    def resolve_path(self, path: Path) -> Path:
        """Resolve path to absolute form."""
        return path.resolve()

    def normalize_path(self, path: Path) -> str:
        """Normalize path to POSIX-style string."""
        return self._normalize(path)

    def get_mtime(self, path: Path) -> float:
        """Get file modification time."""
        normalized = self._normalize(path)
        if normalized not in self.mtimes:
            raise FileNotFoundError(f"{path}")
        return self.mtimes[normalized]


@contextmanager
def atomic_write(target_path: Path) -> Generator[Path, None, None]:
    """Context manager for atomic file writes.

    Writes to a temporary file and atomically moves it to target_path on success.
    If an exception occurs, the temporary file is cleaned up without modifying target.

    Args:
        target_path: Final destination path for the file

    Yields:
        Path to temporary file for writing

    Returns:
        None (context manager)

    Example:
        with atomic_write(Path("output.txt")) as tmp:
            tmp.write_text("content")
        # File is now at output.txt
    """
    # Create temporary file in same directory as target for atomic rename
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path_str = tempfile.mkstemp(
        dir=target_path.parent,
        prefix=".tmp_",
        suffix=target_path.suffix,
    )
    temp_path = Path(temp_path_str)

    try:
        # Close the file descriptor since we'll be using Path for writing
        import os
        os.close(temp_fd)
        yield temp_path
        # Atomic rename (or copy on Windows)
        temp_path.replace(target_path)
    finally:
        # Clean up temporary file on error; missing_ok avoids issues after successful replace
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            # Ignore cleanup errors
            pass


@contextmanager
def temporary_directory() -> Generator[Path, None, None]:
    """Context manager for temporary directory creation and cleanup.

    Creates a temporary directory and ensures it's cleaned up on exit,
    even if exceptions occur.

    Yields:
        Path to temporary directory

    Returns:
        None (context manager)

    Example:
        with temporary_directory() as tmpdir:
            output_file = tmpdir / "output.txt"
            output_file.write_text("data")
        # tmpdir is cleaned up automatically
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        yield temp_path
    finally:
        try:
            shutil.rmtree(temp_path, ignore_errors=False)
        except OSError:
            # Attempt cleanup even if it partially fails
            shutil.rmtree(temp_path, ignore_errors=True)
