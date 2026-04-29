"""Integration tests for Lineage MCP server.

Tests that verify cross-module interactions and complete workflows.
"""

import sys
import time
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestInstructionFileIntegration(unittest.TestCase):
    """Tests for instruction file discovery during reads."""

    def test_read_includes_instruction_files_from_parents(self) -> None:
        """Verify reading file includes parent instruction files."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            ws.create_file("parent/AGENTS.md", "# Parent Instructions\nDo this.")
            ws.create_file("parent/child/test.txt", "File content")

            result = run_async(read_file("parent/child/test.txt"))

            self.assertIn("File content", result)
            self.assertIn("Parent Instructions", result)
            session.clear()

    def test_second_read_keeps_instruction_file_visible_by_path(self) -> None:
        """Verify a repeated read still advertises the instruction file path."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            agents_path = ws.create_file("parent/AGENTS.md", "# Parent Instructions\nDo this.")
            ws.create_file("parent/child/test.txt", "File content")

            run_async(read_file("parent/child/test.txt"))
            result = run_async(read_file("parent/child/test.txt"))

            self.assertIn("Instruction file available", result)
            self.assertIn(str(agents_path), result)
            self.assertNotIn("Parent Instructions", result)
            session.clear()


class TestChangeDetectionIntegration(unittest.TestCase):
    """Tests for change detection across read/modify operations."""

    def test_external_modification_detected_on_subsequent_read(self) -> None:
        """Verify external file changes are detected."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from path_utils import get_file_mtime_ms
            from session_state import session

            session.clear()

            file_path = ws.create_file("test.txt", "original")

            mtime = get_file_mtime_ms(file_path)
            session.track_file(str(file_path), mtime, "original")

            time.sleep(0.1)
            file_path.write_text("modified externally", encoding="utf-8")

            changed = get_changed_files()

            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["status"], "modified")
            self.assertIn("changedLineRanges", changed[0])

            session.clear()

    def test_modify_then_external_change_detected(self) -> None:
        """Verify external changes are detected after our modifications."""
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from session_state import session
            from tools.modify import modify

            session.clear()

            ws.create_file("test.txt", "Hello, World!")

            run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "match_text": "World",
                    "text": "Python",
                }
            ]))

            changed = get_changed_files()
            self.assertEqual(len(changed), 0)

            time.sleep(0.1)
            file_path = ws.path / "test.txt"
            file_path.write_text("External override", encoding="utf-8")

            changed = get_changed_files()
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["status"], "modified")

            session.clear()


if __name__ == "__main__":
    unittest.main()
