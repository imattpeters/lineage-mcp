"""Tests for tools/read_file.py module.

Tests the read file tool including basic reading, line numbers,
partial reading, error handling, and session management.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestReadFileBasic(unittest.TestCase):
    """Tests for basic file reading operations."""

    def test_read_file_returns_content(self) -> None:
        """Verify file content is returned."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "Hello, World!")

            result = run_async(read_file("test.txt"))

            self.assertIn("Hello, World!", result)
            session.clear()

    def test_read_file_not_found_returns_error(self) -> None:
        """Verify error is returned for non-existent file."""
        with TempWorkspace():
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            result = run_async(read_file("nonexistent.txt"))

            self.assertIn("Error", result)
            self.assertIn("not found", result.lower())
            session.clear()


class TestReadFileLineNumbers(unittest.TestCase):
    """Tests for line number formatting."""

    def test_read_file_with_line_numbers(self) -> None:
        """Verify line numbers are formatted correctly."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "line1\nline2\nline3")

            result = run_async(read_file("test.txt", show_line_numbers=True))

            self.assertIn("1→line1", result)
            self.assertIn("2→line2", result)
            self.assertIn("3→line3", result)
            session.clear()

    def test_line_numbers_without_padding(self) -> None:
        """Verify line numbers don't have unnecessary padding."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "a\nb\nc")

            result = run_async(read_file("test.txt", show_line_numbers=True))

            # Should be "1→" not "     1→"
            self.assertIn("1→a", result)
            self.assertNotIn("     1→", result)
            session.clear()


class TestReadFilePartial(unittest.TestCase):
    """Tests for partial file reading with offset and limit."""

    def test_read_file_partial_with_offset(self) -> None:
        """Verify offset skips lines correctly."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "line0\nline1\nline2\nline3\nline4")

            result = run_async(
                read_file("test.txt", offset=2, limit=2, show_line_numbers=True)
            )

            self.assertIn("3→line2", result)  # 0-based offset 2 = line 3
            self.assertIn("4→line3", result)
            self.assertNotIn("line0", result)
            self.assertNotIn("line4", result)
            session.clear()

    def test_read_file_offset_beyond_eof_returns_empty(self) -> None:
        """Verify offset beyond EOF returns empty content."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "line1\nline2")

            result = run_async(read_file("test.txt", offset=100))

            # Should be empty (no content) but not error
            self.assertNotIn("Error", result)
            session.clear()

    def test_read_file_negative_offset_returns_error(self) -> None:
        """Verify negative offset returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "content")

            result = run_async(read_file("test.txt", offset=-1))

            self.assertIn("Error", result)
            session.clear()


class TestReadFileSessionManagement(unittest.TestCase):
    """Tests for session state management during reads."""



if __name__ == "__main__":
    unittest.main()
