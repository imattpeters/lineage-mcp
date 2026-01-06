"""Tests for path_utils.py module.

Tests path resolution, security validation, and file metadata operations.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace


class TestPathResolution(unittest.TestCase):
    """Tests for path resolution operations."""

    def test_resolve_path_returns_absolute_path(self) -> None:
        """Verify relative paths are resolved to absolute."""
        with TempWorkspace() as ws:
            from path_utils import resolve_path

            result = resolve_path("subdir/file.txt")

            self.assertTrue(result.success)
            self.assertEqual(result.path, ws.path / "subdir" / "file.txt")

    def test_resolve_path_allows_valid_nested_paths(self) -> None:
        """Verify valid nested paths are allowed."""
        with TempWorkspace() as ws:
            from path_utils import resolve_path

            result = resolve_path("a/b/c/d/file.txt")

            self.assertTrue(result.success)
            self.assertEqual(result.path, ws.path / "a" / "b" / "c" / "d" / "file.txt")


class TestPathSecurity(unittest.TestCase):
    """Tests for path security validation."""

    def test_resolve_path_blocks_traversal_outside_base(self) -> None:
        """Verify directory traversal attacks are blocked."""
        with TempWorkspace():
            from path_utils import resolve_path

            result = resolve_path("../../../etc/passwd")

            self.assertFalse(result.success)
            self.assertIn("outside", result.error.lower())

    def test_resolve_path_blocks_absolute_paths_outside_base(self) -> None:
        """Verify absolute paths outside base are blocked."""
        with TempWorkspace():
            from path_utils import resolve_path

            result = resolve_path("/etc/passwd")

            self.assertFalse(result.success)


class TestFileMtime(unittest.TestCase):
    """Tests for file modification time operations."""

    def test_get_file_mtime_ms_returns_integer(self) -> None:
        """Verify mtime is returned in milliseconds as integer."""
        with TempWorkspace() as ws:
            from path_utils import get_file_mtime_ms

            file_path = ws.create_file("test.txt", "content")
            mtime = get_file_mtime_ms(file_path)

            self.assertIsInstance(mtime, int)
            self.assertGreater(mtime, 0)


if __name__ == "__main__":
    unittest.main()
