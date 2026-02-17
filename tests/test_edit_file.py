"""Tests for tools/edit_file.py module.

Tests the edit file tool including string replacement,
replace_all mode, error handling, and cache updates.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestEditFileBasic(unittest.TestCase):
    """Tests for basic file editing operations."""

    def test_edit_file_replaces_string(self) -> None:
        """Verify string replacement works."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.edit_file import edit_file

            session.clear()
            file_path = ws.create_file("test.txt", "Hello, World!")

            result = run_async(edit_file("test.txt", "World", "Python"))

            self.assertIn("Successfully", result)
            self.assertEqual(file_path.read_text(), "Hello, Python!")
            session.clear()

    def test_edit_file_string_not_found_returns_error(self) -> None:
        """Verify error when string is not found."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.edit_file import edit_file

            session.clear()
            ws.create_file("test.txt", "Hello, World!")

            result = run_async(edit_file("test.txt", "NotFound", "replacement"))

            self.assertIn("Error", result)
            self.assertIn("not found", result.lower())
            session.clear()


class TestEditFileMultipleOccurrences(unittest.TestCase):
    """Tests for handling multiple occurrences."""

    def test_edit_file_multiple_occurrences_requires_replace_all(self) -> None:
        """Verify multiple occurrences without replace_all returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.edit_file import edit_file

            session.clear()
            ws.create_file("test.txt", "foo bar foo")

            result = run_async(edit_file("test.txt", "foo", "baz"))

            self.assertIn("Error", result)
            self.assertIn("2 times", result)
            session.clear()

    def test_edit_file_replace_all_replaces_all_occurrences(self) -> None:
        """Verify replace_all=True replaces all occurrences."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.edit_file import edit_file

            session.clear()
            file_path = ws.create_file("test.txt", "foo bar foo")

            result = run_async(edit_file("test.txt", "foo", "baz", replace_all=True))

            self.assertIn("Successfully", result)
            self.assertIn("2 occurrence", result)
            self.assertEqual(file_path.read_text(), "baz bar baz")
            session.clear()


class TestEditFileCacheManagement(unittest.TestCase):
    """Tests for cache updates after edits."""

    def test_edit_file_updates_cache(self) -> None:
        """Verify edit updates session cache (no external change reported)."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from session_state import session
            from tools.edit_file import edit_file

            session.clear()
            ws.create_file("test.txt", "Hello, World!")

            run_async(edit_file("test.txt", "World", "Python"))

            # Cache should be updated, so no changes detected
            changed = get_changed_files()
            self.assertEqual(len(changed), 0)

            session.clear()


class TestEditFileSessionManagement(unittest.TestCase):
    """Tests for session state management during edit operations."""



if __name__ == "__main__":
    unittest.main()
