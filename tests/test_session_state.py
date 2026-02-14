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

    def test_clear_resets_cooldown_timer(self) -> None:
        """Verify explicit clear() resets the cooldown timer."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()  # Sets timer
        self.assertIsNotNone(state.last_new_session_time)

        state.clear()
        self.assertIsNone(state.last_new_session_time)


class TestNewSessionCooldown(unittest.TestCase):
    """Tests for new_session cooldown behavior."""

    def test_first_try_new_session_clears(self) -> None:
        """Verify first try_new_session() clears caches."""
        from session_state import SessionState

        state = SessionState()
        state.track_file("/test/file.txt", 12345, "content")
        state.mark_folder_provided("/test/folder")

        result = state.try_new_session()

        self.assertTrue(result)
        self.assertEqual(len(state.mtimes), 0)
        self.assertEqual(len(state.contents), 0)
        self.assertEqual(len(state.provided_folders), 0)
        self.assertIsNotNone(state.last_new_session_time)

    def test_second_try_within_cooldown_is_suppressed(self) -> None:
        """Verify second try_new_session() within cooldown is ignored."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()

        # Add data after first clear
        state.track_file("/test/file.txt", 12345, "content")

        result = state.try_new_session()

        self.assertFalse(result)
        # Data should still be there (clear was suppressed)
        self.assertIn("/test/file.txt", state.mtimes)

    def test_try_after_cooldown_expires_clears(self) -> None:
        """Verify try_new_session() clears after cooldown expires."""
        import time
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()

        # Manually set timer to the past (beyond cooldown)
        state.last_new_session_time = time.monotonic() - 60

        state.track_file("/test/file.txt", 12345, "content")

        result = state.try_new_session()

        self.assertTrue(result)
        self.assertEqual(len(state.mtimes), 0)

    def test_explicit_clear_then_try_new_session_works(self) -> None:
        """Verify clear() resets cooldown so try_new_session() works again."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()

        # Explicit clear resets timer
        state.clear()

        state.track_file("/test/file.txt", 12345, "content")

        result = state.try_new_session()

        self.assertTrue(result)
        self.assertEqual(len(state.mtimes), 0)


class TestNewSessionClearCount(unittest.TestCase):
    """Tests for new_session_clear_count tracking and base instruction file inclusion."""

    def test_initial_clear_count_is_zero(self) -> None:
        """Verify fresh session has clear count of 0."""
        from session_state import SessionState

        state = SessionState()
        self.assertEqual(state.new_session_clear_count, 0)

    def test_try_new_session_increments_clear_count(self) -> None:
        """Verify try_new_session() increments clear count when it actually clears."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()
        self.assertEqual(state.new_session_clear_count, 1)

    def test_suppressed_try_new_session_does_not_increment(self) -> None:
        """Verify suppressed try_new_session() (within cooldown) does not increment."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()
        self.assertEqual(state.new_session_clear_count, 1)

        # Second call within cooldown - suppressed
        state.try_new_session()
        self.assertEqual(state.new_session_clear_count, 1)

    def test_clear_increments_clear_count(self) -> None:
        """Verify explicit clear() increments clear count."""
        from session_state import SessionState

        state = SessionState()
        state.clear()
        self.assertEqual(state.new_session_clear_count, 1)

    def test_clear_count_survives_clear(self) -> None:
        """Verify clear count is never reset by clear() or try_new_session()."""
        import time
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()  # count = 1
        self.assertEqual(state.new_session_clear_count, 1)

        state.clear()  # count = 2
        self.assertEqual(state.new_session_clear_count, 2)

        state.try_new_session()  # count = 3 (cooldown was reset by clear)
        self.assertEqual(state.new_session_clear_count, 3)

    def test_should_include_base_instruction_files_false_initially(self) -> None:
        """Verify base instruction files not included on first session."""
        from session_state import SessionState

        state = SessionState()
        self.assertFalse(state.should_include_base_instruction_files())

    def test_should_include_base_instruction_files_false_after_first_clear(self) -> None:
        """Verify base instruction files not included after first clear only."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()
        self.assertFalse(state.should_include_base_instruction_files())

    def test_should_include_base_instruction_files_true_after_second_clear(self) -> None:
        """Verify base instruction files included after second clear (compaction)."""
        import time
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()  # count = 1

        # Simulate cooldown expiry
        state.last_new_session_time = time.monotonic() - 60

        state.try_new_session()  # count = 2
        self.assertTrue(state.should_include_base_instruction_files())

    def test_should_include_base_instruction_files_true_via_explicit_clear(self) -> None:
        """Verify base instruction files included when second clear is via clear()."""
        from session_state import SessionState

        state = SessionState()
        state.try_new_session()  # count = 1
        state.clear()  # count = 2
        self.assertTrue(state.should_include_base_instruction_files())


if __name__ == "__main__":
    unittest.main()
