"""Tests for tools/delete_file.py module.

Tests the delete file tool including file deletion,
directory deletion, and error handling.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestDeleteFileBasic(unittest.TestCase):
    """Tests for basic file deletion."""

    def test_delete_file_removes_file(self) -> None:
        """Verify file is deleted."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.delete_file import delete_file

            session.clear()

            file_path = workspace.create_file("to_delete.txt", "content")
            self.assertTrue(file_path.exists())

            result = run_async(delete_file("to_delete.txt"))

            self.assertIn("Success", result)
            self.assertFalse(file_path.exists())

            session.clear()


class TestDeleteFileDirectory(unittest.TestCase):
    """Tests for directory deletion."""

    def test_delete_empty_directory(self) -> None:
        """Verify empty directory is deleted."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.delete_file import delete_file

            session.clear()

            dir_path = workspace.create_dir("empty_folder")
            self.assertTrue(dir_path.exists())

            result = run_async(delete_file("empty_folder"))

            self.assertIn("Success", result)
            self.assertFalse(dir_path.exists())

            session.clear()

    def test_delete_nonempty_directory_returns_error(self) -> None:
        """Verify non-empty directory cannot be deleted."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.delete_file import delete_file

            session.clear()

            workspace.create_file("folder/file.txt", "content")

            result = run_async(delete_file("folder"))

            self.assertIn("Error", result)
            # Folder should still exist
            self.assertTrue((workspace.path / "folder").exists())

            session.clear()


class TestDeleteFileErrors(unittest.TestCase):
    """Tests for delete file error handling."""

    def test_delete_nonexistent_file_returns_error(self) -> None:
        """Verify error when file doesn't exist."""
        with TempWorkspace():
            from session_state import session
            from tools.delete_file import delete_file

            session.clear()

            result = run_async(delete_file("nonexistent.txt"))

            self.assertIn("Error", result)

            session.clear()


class TestDeleteFileCacheManagement(unittest.TestCase):
    """Tests for cache updates after deletions."""

    def test_delete_file_removes_from_cache(self) -> None:
        """Verify deleted file is removed from session cache."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.delete_file import delete_file
            from tools.read_file import read_file

            session.clear()

            workspace.create_file("tracked.txt", "content")

            # Read to add to cache
            run_async(read_file("tracked.txt"))
            file_path = str(workspace.path / "tracked.txt")
            self.assertIn(file_path, session.mtimes)

            # Delete should remove from cache
            run_async(delete_file("tracked.txt"))
            self.assertNotIn(file_path, session.mtimes)

            session.clear()


class TestDeleteFileSessionManagement(unittest.TestCase):
    """Tests for session state management during delete operations."""

    def test_new_session_clears_caches(self) -> None:
        """Verify new_session=True clears all tracking."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.delete_file import delete_file

            # Track some files and folders
            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            ws.create_file("to_delete.txt", "content")

            run_async(delete_file("to_delete.txt", new_session=True))

            # Previous tracking should be cleared
            self.assertNotIn("/some/file.txt", session.mtimes)
            self.assertFalse(session.is_folder_provided("/some/folder"))

            session.clear()


if __name__ == "__main__":
    unittest.main()
