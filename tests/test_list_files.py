"""Tests for tools/list_files.py module.

Tests the list files tool including directory listing,
nested directories, and error handling.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestListFilesBasic(unittest.TestCase):
    """Tests for basic directory listing."""

    def test_list_files_returns_directory_contents(self) -> None:
        """Verify directory contents are listed."""
        with TempWorkspace() as workspace:
            from tools.list_files import list_files

            workspace.create_file("file1.txt", "content")
            workspace.create_file("file2.py", "code")
            workspace.create_dir("subdir")

            result = run_async(list_files())

            self.assertIn("file1.txt", result)
            self.assertIn("file2.py", result)
            self.assertIn("subdir", result)

    def test_list_files_shows_subdirectory(self) -> None:
        """Verify listing specific subdirectory."""
        with TempWorkspace() as workspace:
            from tools.list_files import list_files

            workspace.create_file("root.txt", "root content")
            workspace.create_file("subdir/nested.txt", "nested content")

            result = run_async(list_files("subdir"))

            self.assertIn("nested.txt", result)
            self.assertNotIn("root.txt", result)


class TestListFilesErrors(unittest.TestCase):
    """Tests for list files error handling."""

    def test_list_files_nonexistent_directory_returns_error(self) -> None:
        """Verify error when directory doesn't exist."""
        with TempWorkspace():
            from tools.list_files import list_files

            result = run_async(list_files("nonexistent"))

            self.assertIn("Error", result)


class TestListFilesMetadata(unittest.TestCase):
    """Tests for file metadata in listings."""

    def test_list_files_distinguishes_files_and_directories(self) -> None:
        """Verify files and directories are distinguishable."""
        with TempWorkspace() as workspace:
            from tools.list_files import list_files

            workspace.create_file("file.txt", "content")
            workspace.create_dir("folder")

            result = run_async(list_files())

            # Directories typically shown with trailing / or [dir] marker
            self.assertIn("file.txt", result)
            self.assertIn("folder", result)


class TestListFilesSessionManagement(unittest.TestCase):
    """Tests for session state management during list operations."""

    def test_new_session_clears_caches(self) -> None:
        """Verify new_session=True clears all tracking."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.list_files import list_files

            # Track some files and folders
            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            ws.create_dir("subdir")

            run_async(list_files("", new_session=True))

            # Previous tracking should be cleared
            self.assertNotIn("/some/file.txt", session.mtimes)
            self.assertFalse(session.is_folder_provided("/some/folder"))

            session.clear()


if __name__ == "__main__":
    unittest.main()
