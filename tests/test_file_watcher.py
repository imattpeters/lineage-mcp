"""Tests for file_watcher.py module.

Tests file change detection including modified, deleted, and unchanged files,
as well as line range calculation.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace


class TestChangeDetection(unittest.TestCase):
    """Tests for file change detection."""

    def test_detect_modified_file(self) -> None:
        """Verify modified files are detected."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from path_utils import get_file_mtime_ms
            from session_state import session

            session.clear()

            # Create and track a file
            file_path = ws.create_file("test.txt", "initial content")
            mtime = get_file_mtime_ms(file_path)
            session.track_file(str(file_path), mtime - 1000, "old content")

            changed = get_changed_files()

            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["path"], str(file_path))
            self.assertEqual(changed[0]["status"], "modified")

            session.clear()

    def test_detect_deleted_file(self) -> None:
        """Verify deleted files are detected."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from session_state import session

            session.clear()

            # Track a file that doesn't exist
            fake_path = ws.path / "deleted.txt"
            session.track_file(str(fake_path), 12345, "content")

            changed = get_changed_files()

            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["status"], "deleted")

            session.clear()

    def test_no_changes_when_mtime_unchanged(self) -> None:
        """Verify no changes reported when file unchanged."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from path_utils import get_file_mtime_ms
            from session_state import session

            session.clear()

            file_path = ws.create_file("test.txt", "content")
            mtime = get_file_mtime_ms(file_path)
            session.track_file(str(file_path), mtime, "content")

            changed = get_changed_files()

            self.assertEqual(len(changed), 0)

            session.clear()


class TestLineRangeCalculation(unittest.TestCase):
    """Tests for line range calculation in diffs."""

    def test_changed_line_ranges_simple_modification(self) -> None:
        """Verify line ranges are calculated for simple changes."""
        from file_watcher import calculate_changed_line_ranges

        old_content = "line1\nline2\nline3"
        new_content = "line1\nMODIFIED\nline3"

        ranges = calculate_changed_line_ranges(old_content, new_content)

        # Should indicate changes around line 2
        self.assertIn("2", ranges)

    def test_changed_line_ranges_addition(self) -> None:
        """Verify line ranges for added lines."""
        from file_watcher import calculate_changed_line_ranges

        old_content = "line1\nline2"
        new_content = "line1\nline2\nline3"

        ranges = calculate_changed_line_ranges(old_content, new_content)

        # Should indicate addition at end
        self.assertIn("3", ranges)

    def test_changed_line_ranges_deletion(self) -> None:
        """Verify line ranges for deleted lines."""
        from file_watcher import calculate_changed_line_ranges

        old_content = "line1\nline2\nline3"
        new_content = "line1\nline3"

        ranges = calculate_changed_line_ranges(old_content, new_content)

        # Should indicate change around line 2
        self.assertIn("2", ranges)


if __name__ == "__main__":
    unittest.main()
