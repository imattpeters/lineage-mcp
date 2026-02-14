"""Tests for instruction_files.py module.

Tests instruction file discovery including parent traversal,
priority order, and deduplication.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace


class TestInstructionFileDiscovery(unittest.TestCase):
    """Tests for finding instruction files in parent directories."""

    def test_find_instruction_files_in_parent_directory(self) -> None:
        """Verify instruction files are found walking up."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents

            # Create structure: parent/AGENTS.md, parent/child/file.txt
            parent = ws.create_dir("parent")
            agents_md = ws.create_file("parent/AGENTS.md", "# Instructions")
            test_file = ws.create_file("parent/child/test.txt", "content")

            found = find_instruction_files_in_parents(test_file)

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0][0], parent)
            self.assertEqual(found[0][1], agents_md)

    def test_instruction_file_at_base_dir_excluded(self) -> None:
        """Verify instruction files at BASE_DIR are not included on first session."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents
            from session_state import session

            # Ensure we're simulating a fresh session (no compaction yet)
            old_count = session.new_session_clear_count
            session.new_session_clear_count = 0

            try:
                # Create AGENTS.md at base and a file at base
                ws.create_file("AGENTS.md", "# Root Instructions")
                test_file = ws.create_file("test.txt", "content")

                found = find_instruction_files_in_parents(test_file)

                self.assertEqual(len(found), 0)
            finally:
                session.new_session_clear_count = old_count

    def test_multiple_parents_discovered(self) -> None:
        """Verify instruction files from multiple parent levels are found."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents

            # Create nested structure with instruction files at each level
            ws.create_file("level1/AGENTS.md", "# Level 1")
            ws.create_file("level1/level2/AGENTS.md", "# Level 2")
            test_file = ws.create_file("level1/level2/level3/test.txt", "content")

            found = find_instruction_files_in_parents(test_file)

            # Should find both (not base dir)
            self.assertEqual(len(found), 2)


class TestInstructionFilePriority(unittest.TestCase):
    """Tests for instruction file priority order."""

    def test_priority_order_selects_first_match(self) -> None:
        """Verify higher priority files are selected over lower."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents

            # Create both AGENTS.md and CLAUDE.md in same directory
            parent = ws.create_dir("parent")
            agents_md = ws.create_file("parent/AGENTS.md", "# AGENTS")
            ws.create_file("parent/CLAUDE.md", "# CLAUDE")
            test_file = ws.create_file("parent/child/test.txt", "content")

            found = find_instruction_files_in_parents(test_file)

            # Should only find AGENTS.md (higher priority)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0][1], agents_md)


class TestInstructionFileDeduplication(unittest.TestCase):
    """Tests for preventing duplicate instruction file inclusion."""

    def test_folder_not_provided_twice(self) -> None:
        """Verify same folder instruction file is only included once."""
        with TempWorkspace() as ws:
            from instruction_files import (
                find_instruction_files_in_parents,
                include_instruction_file_content,
            )
            from session_state import session

            session.clear()

            ws.create_file("parent/AGENTS.md", "# Instructions")
            test_file = ws.create_file("parent/child/test.txt", "content")

            # First time: should include
            found = find_instruction_files_in_parents(test_file)
            content1 = include_instruction_file_content(found)
            self.assertIn("Instructions", content1)

            # Second time: folder already provided
            found = find_instruction_files_in_parents(test_file)
            content2 = include_instruction_file_content(found)
            self.assertEqual(content2, "")

            session.clear()


class TestBaseDirectoryInstructionFiles(unittest.TestCase):
    """Tests for base directory instruction file inclusion after compaction."""

    def test_base_dir_excluded_on_first_session(self) -> None:
        """Verify base dir instruction files excluded on initial session."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents
            from session_state import session

            # Reset to fresh state
            old_count = session.new_session_clear_count
            session.new_session_clear_count = 0

            try:
                ws.create_file("AGENTS.md", "# Root Instructions")
                test_file = ws.create_file("test.txt", "content")

                found = find_instruction_files_in_parents(test_file)
                self.assertEqual(len(found), 0)
            finally:
                session.new_session_clear_count = old_count

    def test_base_dir_excluded_after_first_clear(self) -> None:
        """Verify base dir instruction files still excluded after only one clear."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents
            from session_state import session

            old_count = session.new_session_clear_count
            session.new_session_clear_count = 1

            try:
                ws.create_file("AGENTS.md", "# Root Instructions")
                test_file = ws.create_file("test.txt", "content")

                found = find_instruction_files_in_parents(test_file)
                self.assertEqual(len(found), 0)
            finally:
                session.new_session_clear_count = old_count

    def test_base_dir_included_after_second_clear(self) -> None:
        """Verify base dir instruction files included after compaction (2nd clear)."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents
            from session_state import session

            old_count = session.new_session_clear_count
            session.new_session_clear_count = 2

            try:
                base_agents = ws.create_file("AGENTS.md", "# Root Instructions")
                test_file = ws.create_file("test.txt", "content")

                found = find_instruction_files_in_parents(test_file)

                self.assertEqual(len(found), 1)
                self.assertEqual(found[0][1], base_agents)
            finally:
                session.new_session_clear_count = old_count

    def test_base_dir_included_alongside_parent_files(self) -> None:
        """Verify base dir files are included together with parent dir files."""
        with TempWorkspace() as ws:
            from instruction_files import find_instruction_files_in_parents
            from session_state import session

            old_count = session.new_session_clear_count
            session.new_session_clear_count = 2

            try:
                base_agents = ws.create_file("AGENTS.md", "# Root")
                parent_agents = ws.create_file("parent/AGENTS.md", "# Parent")
                test_file = ws.create_file("parent/child/test.txt", "content")

                found = find_instruction_files_in_parents(test_file)

                self.assertEqual(len(found), 2)
                # Parent dir file found first, then base dir appended
                self.assertEqual(found[0][1], parent_agents)
                self.assertEqual(found[1][1], base_agents)
            finally:
                session.new_session_clear_count = old_count

    def test_base_dir_deduped_via_provided_folders(self) -> None:
        """Verify base dir instruction file goes through provided_folders dedup."""
        with TempWorkspace() as ws:
            from instruction_files import (
                find_instruction_files_in_parents,
                include_instruction_file_content,
            )
            from session_state import session

            old_count = session.new_session_clear_count
            session.new_session_clear_count = 2
            session.provided_folders.clear()

            try:
                ws.create_file("AGENTS.md", "# Root Instructions")
                test_file = ws.create_file("test.txt", "content")

                # First time: should include base dir
                found = find_instruction_files_in_parents(test_file)
                content1 = include_instruction_file_content(found)
                self.assertIn("Root Instructions", content1)

                # Second time: base dir already provided, should be empty
                found = find_instruction_files_in_parents(test_file)
                content2 = include_instruction_file_content(found)
                self.assertEqual(content2, "")
            finally:
                session.new_session_clear_count = old_count
                session.provided_folders.clear()


if __name__ == "__main__":
    unittest.main()
