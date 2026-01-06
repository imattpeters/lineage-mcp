"""Tests for session_state.py module.

Tests session state management including file tracking, folder tracking,
and cache operations.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


class TestSessionState(unittest.TestCase):
    """Tests for SessionState class."""

    def test_track_file_stores_mtime_and_content(self) -> None:
        """Verify track_file correctly stores mtime and content."""
        from session_state import SessionState

        state = SessionState()
        state.track_file("/path/to/file.txt", 1234567890, "file content")

        self.assertEqual(state.mtimes["/path/to/file.txt"], 1234567890)
        self.assertEqual(state.contents["/path/to/file.txt"], "file content")

    def test_untrack_file_removes_from_all_caches(self) -> None:
        """Verify untrack_file removes mtime and content."""
        from session_state import SessionState

        state = SessionState()
        state.track_file("/path/to/file.txt", 1234567890, "content")
        state.untrack_file("/path/to/file.txt")

        self.assertNotIn("/path/to/file.txt", state.mtimes)
        self.assertNotIn("/path/to/file.txt", state.contents)

    def test_untrack_nonexistent_file_does_not_raise(self) -> None:
        """Verify untracking non-existent file is safe."""
        from session_state import SessionState

        state = SessionState()
        # Should not raise
        state.untrack_file("/nonexistent/file.txt")

    def test_folder_provided_tracking(self) -> None:
        """Verify folder provided tracking works correctly."""
        from session_state import SessionState

        state = SessionState()

        self.assertFalse(state.is_folder_provided("/test/folder"))
        state.mark_folder_provided("/test/folder")
        self.assertTrue(state.is_folder_provided("/test/folder"))

    def test_clear_resets_all_caches(self) -> None:
        """Verify clear removes all state."""
        from session_state import SessionState

        state = SessionState()
        state.track_file("/test/file.txt", 12345, "content")
        state.mark_folder_provided("/test/folder")

        state.clear()

        self.assertEqual(len(state.mtimes), 0)
        self.assertEqual(len(state.contents), 0)
        self.assertEqual(len(state.provided_folders), 0)


if __name__ == "__main__":
    unittest.main()
