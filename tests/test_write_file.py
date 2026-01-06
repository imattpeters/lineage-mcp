"""Tests for tools/write_file.py module.

Tests the write file tool including file creation,
overwriting, directory creation, and cache updates.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestWriteFileBasic(unittest.TestCase):
    """Tests for basic file writing."""

    def test_write_file_creates_new_file(self) -> None:
        """Verify new file is created with content."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.write_file import write_file

            session.clear()

            result = run_async(write_file("new_file.txt", "Hello, World!"))
            file_path = workspace.path / "new_file.txt"

            self.assertIn("Successfully", result)
            self.assertTrue(file_path.exists())
            self.assertEqual(file_path.read_text(), "Hello, World!")

            session.clear()

    def test_write_file_overwrites_existing(self) -> None:
        """Verify existing file is overwritten."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.write_file import write_file

            session.clear()

            file_path = workspace.create_file("existing.txt", "old content")

            result = run_async(write_file("existing.txt", "new content"))

            self.assertIn("Successfully", result)
            self.assertEqual(file_path.read_text(), "new content")

            session.clear()


class TestWriteFileDirectories(unittest.TestCase):
    """Tests for directory creation during writes."""

    def test_write_file_creates_parent_directories(self) -> None:
        """Verify parent directories are created if missing."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.write_file import write_file

            session.clear()

            result = run_async(write_file("deep/nested/path/file.txt", "content"))
            file_path = workspace.path / "deep" / "nested" / "path" / "file.txt"

            self.assertIn("Successfully", result)
            self.assertTrue(file_path.exists())
            self.assertEqual(file_path.read_text(), "content")

            session.clear()


class TestWriteFileCacheManagement(unittest.TestCase):
    """Tests for cache updates after writes."""

    def test_write_file_updates_cache(self) -> None:
        """Verify write updates session cache (no external change reported)."""
        with TempWorkspace() as workspace:
            from file_watcher import get_changed_files
            from session_state import session
            from tools.write_file import write_file

            session.clear()

            run_async(write_file("test.txt", "initial content"))

            # Cache should be updated, so no changes detected
            changed = get_changed_files()
            self.assertEqual(len(changed), 0)

            session.clear()


class TestWriteFileSessionManagement(unittest.TestCase):
    """Tests for session state management during write operations."""

    def test_new_session_clears_caches(self) -> None:
        """Verify new_session=True clears all tracking."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.write_file import write_file

            # Track some files and folders
            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            run_async(write_file("test.txt", "content", new_session=True))

            # Previous tracking should be cleared
            self.assertNotIn("/some/file.txt", session.mtimes)
            self.assertFalse(session.is_folder_provided("/some/folder"))

            session.clear()


if __name__ == "__main__":
    unittest.main()
