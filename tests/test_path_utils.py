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

from path_utils import resolve_path


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


class TestAllowFullPaths(unittest.TestCase):
    """Tests for allowFullPaths path resolution."""

    def test_allows_traversal_when_enabled(self) -> None:
        """Verify paths outside base are allowed when allowFullPaths is True."""
        import path_utils

        with TempWorkspace():
            old_allow = path_utils._allow_full_paths
            path_utils._allow_full_paths = True
            try:
                result = resolve_path("../../../etc/passwd")

                self.assertTrue(result.success)
            finally:
                path_utils._allow_full_paths = old_allow

    def test_allows_absolute_paths_when_enabled(self) -> None:
        """Verify absolute paths outside base are allowed when allowFullPaths is True."""
        import path_utils

        with TempWorkspace():
            old_allow = path_utils._allow_full_paths
            path_utils._allow_full_paths = True
            try:
                if sys.platform == "win32":
                    result = resolve_path("C:\\Windows\\System32")
                else:
                    result = resolve_path("/etc/passwd")

                self.assertTrue(result.success)
            finally:
                path_utils._allow_full_paths = old_allow

    def test_still_resolves_relative_paths_when_enabled(self) -> None:
        """Verify relative paths still resolve against base dir when allowFullPaths is True."""
        import path_utils

        with TempWorkspace() as ws:
            old_allow = path_utils._allow_full_paths
            path_utils._allow_full_paths = True
            try:
                result = resolve_path("subdir/file.txt")

                self.assertTrue(result.success)
                self.assertEqual(result.path, ws.path / "subdir" / "file.txt")
            finally:
                path_utils._allow_full_paths = old_allow

    def test_blocks_traversal_when_disabled(self) -> None:
        """Verify paths outside base are blocked when allowFullPaths is False."""
        import path_utils

        with TempWorkspace():
            old_allow = path_utils._allow_full_paths
            path_utils._allow_full_paths = False
            try:
                result = resolve_path("../../../etc/passwd")

                self.assertFalse(result.success)
            finally:
                path_utils._allow_full_paths = old_allow

    def test_set_allow_full_paths(self) -> None:
        """Verify set_allow_full_paths updates the global flag."""
        import path_utils
        from path_utils import get_allow_full_paths, set_allow_full_paths

        old_allow = path_utils._allow_full_paths
        try:
            set_allow_full_paths(True)
            self.assertTrue(get_allow_full_paths())

            set_allow_full_paths(False)
            self.assertFalse(get_allow_full_paths())
        finally:
            path_utils._allow_full_paths = old_allow


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

    def test_get_file_mtime_ms_magnitude(self) -> None:
        """Verify mtime is in milliseconds, not seconds or nanoseconds."""
        with TempWorkspace() as ws:
            from path_utils import get_file_mtime_ms
            import time

            file_path = ws.create_file("test.txt", "content")
            mtime_ms = get_file_mtime_ms(file_path)
            current_time_ms = int(time.time() * 1000)

            # Mtime should be close to current time in milliseconds
            # Should be within ~10 seconds (10000 ms) of now
            self.assertLess(abs(mtime_ms - current_time_ms), 10000)

            # Sanity check: should be in milliseconds range (not seconds or nanoseconds)
            # A reasonable file mtime is between Jan 2000 and Dec 2100
            # In ms: 946684800000 to 4102444800000
            self.assertGreater(mtime_ms, 946684800000)
            self.assertLess(mtime_ms, 4102444800000)

    def test_get_file_mtime_ms_precision(self) -> None:
        """Verify mtime retains millisecond precision from st_mtime_ns."""
        with TempWorkspace() as ws:
            from path_utils import get_file_mtime_ms

            file_path = ws.create_file("test.txt", "content")

            # Get both the raw stat and the converted mtime
            stat = file_path.stat()
            mtime_ms = get_file_mtime_ms(file_path)

            # Verify the conversion is correct: st_mtime_ns / 1_000_000
            expected_mtime = int(stat.st_mtime_ns / 1_000_000)
            self.assertEqual(mtime_ms, expected_mtime)

    def test_get_file_mtime_ms_different_files_different_mtimes(self) -> None:
        """Verify different files can have different mtimes."""
        import time
        with TempWorkspace() as ws:
            from path_utils import get_file_mtime_ms

            file1 = ws.create_file("test1.txt", "content1")
            mtime1 = get_file_mtime_ms(file1)

            # Small sleep to ensure different mtime
            time.sleep(0.01)

            file2 = ws.create_file("test2.txt", "content2")
            mtime2 = get_file_mtime_ms(file2)

            # file2 should have a later mtime
            self.assertGreater(mtime2, mtime1)


if __name__ == "__main__":
    unittest.main()
