"""Tests for tools/search_files.py module.

Tests the search files tool including glob patterns,
subdirectory search, and error handling.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestSearchFilesBasic(unittest.TestCase):
    """Tests for basic file searching."""

    def test_search_files_finds_by_extension(self) -> None:
        """Verify files are found by extension pattern."""
        with TempWorkspace() as workspace:
            from tools.search_files import search_files

            workspace.create_file("app.py", "python code")
            workspace.create_file("utils.py", "utilities")
            workspace.create_file("config.json", "json config")

            result = run_async(search_files("*.py"))

            self.assertIn("app.py", result)
            self.assertIn("utils.py", result)
            self.assertNotIn("config.json", result)

    def test_search_files_recursive_pattern(self) -> None:
        """Verify recursive glob pattern finds nested files."""
        with TempWorkspace() as workspace:
            from tools.search_files import search_files

            workspace.create_file("root.py", "root")
            workspace.create_file("src/app.py", "app")
            workspace.create_file("src/utils/helpers.py", "helpers")

            result = run_async(search_files("**/*.py"))

            self.assertIn("root.py", result)
            self.assertIn("app.py", result)
            self.assertIn("helpers.py", result)


class TestSearchFilesSubdirectory(unittest.TestCase):
    """Tests for searching within subdirectories."""

    def test_search_files_within_path(self) -> None:
        """Verify search is limited to specified path."""
        with TempWorkspace() as workspace:
            from tools.search_files import search_files

            workspace.create_file("root.txt", "root content")
            workspace.create_file("docs/readme.txt", "readme")
            workspace.create_file("docs/guide.txt", "guide")

            result = run_async(search_files("*.txt", path="docs"))

            self.assertIn("readme.txt", result)
            self.assertIn("guide.txt", result)
            self.assertNotIn("root.txt", result)


class TestSearchFilesNoResults(unittest.TestCase):
    """Tests for search with no matching files."""

    def test_search_files_no_matches(self) -> None:
        """Verify appropriate response when no files match."""
        with TempWorkspace() as workspace:
            from tools.search_files import search_files

            workspace.create_file("test.txt", "content")

            result = run_async(search_files("*.xyz"))

            # Should indicate no matches found (not error)
            self.assertNotIn("test.txt", result)


class TestSearchFilesSessionManagement(unittest.TestCase):
    """Tests for session state management during search operations."""



if __name__ == "__main__":
    unittest.main()
