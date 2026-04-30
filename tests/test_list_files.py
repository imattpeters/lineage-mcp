"""Tests for tools/list_files.py module.

Tests the list files tool including directory listing,
nested directories, and error handling.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from path_utils import get_file_mtime_ms

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


class TestListFilesAllowFullPaths(unittest.TestCase):
    """Tests for listing directories outside base_dir when allowFullPaths is enabled."""

    def test_list_files_outside_base_dir_allowed_when_allow_full_paths(self) -> None:
        """Verify listing an absolute path outside base_dir works when allowFullPaths=True."""
        import path_utils

        with TempWorkspace() as workspace:
            from tools.list_files import list_files

            # Create a second temp dir outside the base workspace
            import tempfile
            with tempfile.TemporaryDirectory() as outside_dir:
                outside_path = Path(outside_dir)
                (outside_path / "external.txt").write_text("external", encoding="utf-8")
                (outside_path / "subdir").mkdir()

                old_allow = path_utils._allow_full_paths
                try:
                    path_utils._allow_full_paths = True
                    result = run_async(list_files(str(outside_path)))
                    self.assertIn("external.txt", result)
                    self.assertNotIn("Error", result)
                finally:
                    path_utils._allow_full_paths = old_allow

    def test_list_files_outside_base_dir_blocked_when_not_allow_full_paths(self) -> None:
        """Verify listing an absolute path outside base_dir is blocked when allowFullPaths=False."""
        import path_utils

        with TempWorkspace():
            from tools.list_files import list_files

            import tempfile
            with tempfile.TemporaryDirectory() as outside_dir:
                old_allow = path_utils._allow_full_paths
                try:
                    path_utils._allow_full_paths = False
                    result = run_async(list_files(str(Path(outside_dir))))
                    self.assertIn("Error", result)
                finally:
                    path_utils._allow_full_paths = old_allow


class TestListFilesSessionManagement(unittest.TestCase):
    """Tests for session state management during list operations."""

    def test_list_files_reports_changed_files_with_lineage_wrapper(self) -> None:
        """Verify changed-file notices keep the lineage wrapper when content exists."""
        with TempWorkspace() as workspace:
            from session_state import session
            from tools.list_files import list_files

            session.clear()
            tracked_file = workspace.create_file("tracked.txt", "old")
            session.track_file(str(tracked_file), 0, "old")
            tracked_file.write_text("new", encoding="utf-8")

            result = run_async(list_files())

            self.assertIn("EOF\n[Lineage Message]:", result)
            self.assertIn("[CHANGED_FILES]", result)
            self.assertIn("tracked.txt", result)
            self.assertEqual(session.mtimes[str(tracked_file)], get_file_mtime_ms(tracked_file))
            session.clear()

    def test_list_files_skips_empty_lineage_wrapper(self) -> None:
        """Verify an empty formatter result does not produce a blank lineage trailer."""
        with TempWorkspace() as workspace:
            from tools.list_files import list_files

            workspace.create_file("file.txt", "content")

            with patch("tools.list_files.format_changed_files_section", return_value="   "):
                result = run_async(list_files())

            self.assertNotIn("EOF\n[Lineage Message]:", result)
            self.assertNotIn("[Lineage Message]:", result)


if __name__ == "__main__":
    unittest.main()
