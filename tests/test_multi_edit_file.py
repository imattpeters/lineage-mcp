"""Tests for tools/multi_edit_file.py module.

Tests the multi-edit file tool including batch edits, partial failures,
validation, and cache updates.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestMultiEditFileBasic(unittest.TestCase):
    """Tests for basic multi-edit operations."""

    def test_single_edit_succeeds(self) -> None:
        """Verify a single edit in a batch works."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            file_path = ws.create_file("test.txt", "Hello, World!")

            result = run_async(multi_edit_file([
                {"file_path": "test.txt", "old_string": "World", "new_string": "Python"},
            ]))

            self.assertIn("Successfully", result)
            self.assertIn("1 occurrence", result)
            self.assertEqual(file_path.read_text(), "Hello, Python!")
            session.clear()

    def test_multiple_edits_different_files(self) -> None:
        """Verify edits across multiple files work."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            file_a = ws.create_file("a.txt", "Hello A")
            file_b = ws.create_file("b.txt", "Hello B")

            result = run_async(multi_edit_file([
                {"file_path": "a.txt", "old_string": "Hello A", "new_string": "Changed A"},
                {"file_path": "b.txt", "old_string": "Hello B", "new_string": "Changed B"},
            ]))

            self.assertIn("Edit 1 (a.txt): Successfully", result)
            self.assertIn("Edit 2 (b.txt): Successfully", result)
            self.assertEqual(file_a.read_text(), "Changed A")
            self.assertEqual(file_b.read_text(), "Changed B")
            session.clear()

    def test_multiple_edits_same_file(self) -> None:
        """Verify sequential edits on the same file work."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            file_path = ws.create_file("test.txt", "foo bar baz")

            result = run_async(multi_edit_file([
                {"file_path": "test.txt", "old_string": "foo", "new_string": "FOO"},
                {"file_path": "test.txt", "old_string": "baz", "new_string": "BAZ"},
            ]))

            self.assertIn("Edit 1", result)
            self.assertIn("Edit 2", result)
            self.assertEqual(file_path.read_text(), "FOO bar BAZ")
            session.clear()

    def test_replace_all_in_batch(self) -> None:
        """Verify replace_all works within a batch edit."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            file_path = ws.create_file("test.txt", "aaa bbb aaa")

            result = run_async(multi_edit_file([
                {"file_path": "test.txt", "old_string": "aaa", "new_string": "ccc", "replace_all": True},
            ]))

            self.assertIn("2 occurrence", result)
            self.assertEqual(file_path.read_text(), "ccc bbb ccc")
            session.clear()


class TestMultiEditFileErrors(unittest.TestCase):
    """Tests for error handling in multi-edit."""

    def test_empty_edits_returns_error(self) -> None:
        """Verify empty edit list returns error."""
        with TempWorkspace():
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            result = run_async(multi_edit_file([]))
            self.assertIn("Error", result)
            self.assertIn("No edits", result)
            session.clear()

    def test_missing_file_path_returns_error(self) -> None:
        """Verify missing file_path field returns error for that edit."""
        with TempWorkspace():
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            result = run_async(multi_edit_file([
                {"old_string": "a", "new_string": "b"},
            ]))
            self.assertIn("missing 'file_path'", result)
            session.clear()

    def test_missing_old_string_returns_error(self) -> None:
        """Verify missing old_string field returns error for that edit."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            ws.create_file("test.txt", "content")
            result = run_async(multi_edit_file([
                {"file_path": "test.txt", "new_string": "b"},
            ]))
            self.assertIn("missing 'old_string'", result)
            session.clear()

    def test_file_not_found_reports_error_continues(self) -> None:
        """Verify missing file reports error but other edits continue."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            file_path = ws.create_file("exists.txt", "Hello")

            result = run_async(multi_edit_file([
                {"file_path": "missing.txt", "old_string": "a", "new_string": "b"},
                {"file_path": "exists.txt", "old_string": "Hello", "new_string": "Changed"},
            ]))

            self.assertIn("Edit 1 (missing.txt): Error", result)
            self.assertIn("Edit 2 (exists.txt): Successfully", result)
            self.assertEqual(file_path.read_text(), "Changed")
            session.clear()

    def test_string_not_found_reports_error_continues(self) -> None:
        """Verify string-not-found reports error but other edits continue."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            ws.create_file("a.txt", "Hello")
            file_b = ws.create_file("b.txt", "World")

            result = run_async(multi_edit_file([
                {"file_path": "a.txt", "old_string": "NotFound", "new_string": "x"},
                {"file_path": "b.txt", "old_string": "World", "new_string": "Changed"},
            ]))

            self.assertIn("Edit 1 (a.txt): Error: String not found", result)
            self.assertIn("Edit 2 (b.txt): Successfully", result)
            self.assertEqual(file_b.read_text(), "Changed")
            session.clear()

    def test_ambiguous_replacement_reports_error(self) -> None:
        """Verify ambiguous replacement without replace_all reports error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            ws.create_file("test.txt", "foo foo foo")

            result = run_async(multi_edit_file([
                {"file_path": "test.txt", "old_string": "foo", "new_string": "bar"},
            ]))

            self.assertIn("3 times", result)
            self.assertIn("replace_all", result)
            session.clear()


class TestMultiEditFileSessionManagement(unittest.TestCase):
    """Tests for session state management during multi-edit."""

    def test_new_session_clears_caches(self) -> None:
        """Verify new_session=True clears all tracking."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            ws.create_file("test.txt", "Hello")

            run_async(multi_edit_file(
                [{"file_path": "test.txt", "old_string": "Hello", "new_string": "Hi"}],
                new_session=True,
            ))

            self.assertNotIn("/some/file.txt", session.mtimes)
            self.assertFalse(session.is_folder_provided("/some/folder"))
            session.clear()

    def test_edits_update_cache(self) -> None:
        """Verify multi-edit updates session cache."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from session_state import session
            from tools.multi_edit_file import multi_edit_file

            session.clear()
            ws.create_file("test.txt", "Hello")

            run_async(multi_edit_file([
                {"file_path": "test.txt", "old_string": "Hello", "new_string": "Changed"},
            ]))

            changed = get_changed_files()
            self.assertEqual(len(changed), 0)
            session.clear()


if __name__ == "__main__":
    unittest.main()
