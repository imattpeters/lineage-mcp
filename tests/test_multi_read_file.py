"""Tests for tools/multi_read_file.py module.

Tests the multi-read file tool including batch reading, max file limit,
error handling, and session management.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestMultiReadFileBasic(unittest.TestCase):
    """Tests for basic multi-read operations."""

    def test_read_single_file(self) -> None:
        """Verify reading a single file in a batch works."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("test.txt", "Hello, World!")

            result = run_async(multi_read_file(["test.txt"]))

            self.assertIn("--- test.txt ---", result)
            self.assertIn("Hello, World!", result)
            session.clear()

    def test_read_multiple_files(self) -> None:
        """Verify reading multiple files returns all contents."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("a.txt", "Content A")
            ws.create_file("b.txt", "Content B")
            ws.create_file("c.txt", "Content C")

            result = run_async(multi_read_file(["a.txt", "b.txt", "c.txt"]))

            self.assertIn("--- a.txt ---", result)
            self.assertIn("Content A", result)
            self.assertIn("--- b.txt ---", result)
            self.assertIn("Content B", result)
            self.assertIn("--- c.txt ---", result)
            self.assertIn("Content C", result)
            session.clear()

    def test_read_with_line_numbers(self) -> None:
        """Verify line numbers are applied to all files."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("a.txt", "line1\nline2")
            ws.create_file("b.txt", "alpha\nbeta")

            result = run_async(multi_read_file(
                ["a.txt", "b.txt"], show_line_numbers=True
            ))

            self.assertIn("1→line1", result)
            self.assertIn("2→line2", result)
            self.assertIn("1→alpha", result)
            self.assertIn("2→beta", result)
            session.clear()

    def test_read_five_files_succeeds(self) -> None:
        """Verify reading exactly 5 files works (max limit)."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            for i in range(5):
                ws.create_file(f"file{i}.txt", f"content{i}")

            result = run_async(multi_read_file(
                [f"file{i}.txt" for i in range(5)]
            ))

            for i in range(5):
                self.assertIn(f"--- file{i}.txt ---", result)
                self.assertIn(f"content{i}", result)
            session.clear()


class TestMultiReadFileErrors(unittest.TestCase):
    """Tests for error handling in multi-read."""

    def test_empty_list_returns_error(self) -> None:
        """Verify empty file list returns error."""
        with TempWorkspace():
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            result = run_async(multi_read_file([]))
            self.assertIn("Error", result)
            self.assertIn("No file paths", result)
            session.clear()

    def test_too_many_files_returns_error(self) -> None:
        """Verify more than 5 files returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            for i in range(6):
                ws.create_file(f"file{i}.txt", f"content{i}")

            result = run_async(multi_read_file(
                [f"file{i}.txt" for i in range(6)]
            ))

            self.assertIn("Error", result)
            self.assertIn("Too many files", result)
            self.assertIn("6", result)
            session.clear()

    def test_file_not_found_reports_error_continues(self) -> None:
        """Verify missing file reports error but other files are read."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("exists.txt", "Hello")

            result = run_async(multi_read_file(["missing.txt", "exists.txt"]))

            self.assertIn("--- missing.txt ---", result)
            self.assertIn("Error: File not found", result)
            self.assertIn("--- exists.txt ---", result)
            self.assertIn("Hello", result)
            session.clear()

    def test_mixed_valid_and_invalid_files(self) -> None:
        """Verify mix of valid and invalid files handles gracefully."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("good.txt", "Good content")
            ws.create_dir("adir")

            result = run_async(multi_read_file([
                "good.txt",
                "nonexistent.txt",
                "adir",
            ]))

            self.assertIn("Good content", result)
            self.assertIn("Error: File not found: nonexistent.txt", result)
            self.assertIn("Error: Path is not a file: adir", result)
            session.clear()


class TestMultiReadFileSessionManagement(unittest.TestCase):
    """Tests for session state management during multi-read."""

    def test_new_session_clears_caches(self) -> None:
        """Verify new_session=True clears all tracking."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            ws.create_file("test.txt", "content")

            run_async(multi_read_file(["test.txt"], new_session=True))

            self.assertNotIn("/some/file.txt", session.mtimes)
            self.assertFalse(session.is_folder_provided("/some/folder"))
            session.clear()

    def test_files_are_tracked_after_read(self) -> None:
        """Verify all read files are tracked in session."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.multi_read_file import multi_read_file

            session.clear()
            ws.create_file("a.txt", "content a")
            ws.create_file("b.txt", "content b")

            run_async(multi_read_file(["a.txt", "b.txt"]))

            # Both files should be tracked
            tracked_paths = list(session.mtimes.keys())
            self.assertEqual(len(tracked_paths), 2)
            session.clear()


if __name__ == "__main__":
    unittest.main()
