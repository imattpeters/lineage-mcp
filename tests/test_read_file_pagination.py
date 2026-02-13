"""Tests for cursor-based pagination in read_file tool.

Tests the extract_content_by_cursor helper and read_file integration with cursor pagination.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestExtractContentByCursor(unittest.TestCase):
    """Test the cursor-based content extraction logic."""

    def test_empty_content(self):
        """Empty content returns empty result."""
        from tools.read_file import extract_content_by_cursor

        result = extract_content_by_cursor("", 0, 1000)
        self.assertEqual(result, ("", 0, 0, 0, 0))

    def test_full_content_within_budget(self):
        """Content under budget returns everything."""
        from tools.read_file import extract_content_by_cursor

        content = "Line 1\nLine 2\nLine 3\n"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 1000)
        )
        self.assertEqual(extracted, content)
        self.assertEqual(next_cursor, len(content))
        self.assertEqual(start_line, 0)
        self.assertEqual(end_line, 3)
        self.assertEqual(total_lines, 3)

    def test_cursor_at_start(self):
        """Cursor at 0 starts from beginning."""
        from tools.read_file import extract_content_by_cursor

        content = "AAAA\nBBBB\nCCCC\n"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 10)
        )
        # Budget 10, line 1 is 5 chars, line 2 is 5 chars = 10 total
        self.assertEqual(extracted, "AAAA\nBBBB\n")
        self.assertEqual(next_cursor, 10)
        self.assertEqual(start_line, 0)
        self.assertEqual(end_line, 2)

    def test_cursor_mid_file(self):
        """Cursor in the middle of the file resumes correctly."""
        from tools.read_file import extract_content_by_cursor

        content = "AAAA\nBBBB\nCCCC\n"
        # Start from after line 2 (position 10)
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 10, 1000)
        )
        self.assertEqual(extracted, "CCCC\n")
        self.assertEqual(next_cursor, 15)
        self.assertEqual(start_line, 2)
        self.assertEqual(end_line, 3)

    def test_cursor_beyond_eof(self):
        """Cursor past end of content returns empty."""
        from tools.read_file import extract_content_by_cursor

        content = "AAAA\nBBBB\n"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 100, 1000)
        )
        self.assertEqual(extracted, "")
        self.assertEqual(start_line, total_lines)
        self.assertEqual(end_line, total_lines)

    def test_line_aware_truncation(self):
        """Truncation happens at line boundaries."""
        from tools.read_file import extract_content_by_cursor

        content = "Short\nThis is a much longer line\nTiny\n"
        # Budget 15: "Short\n" = 6 chars, next line = 27 chars, would exceed
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 15)
        )
        self.assertEqual(extracted, "Short\n")
        self.assertEqual(next_cursor, 6)
        self.assertEqual(end_line, 1)

    def test_at_least_one_line(self):
        """Always includes at least one line even if it exceeds budget."""
        from tools.read_file import extract_content_by_cursor

        content = "This is a very long line that exceeds the budget\nShort\n"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 5)
        )
        # Must include at least the first line even though it exceeds budget
        self.assertEqual(extracted, "This is a very long line that exceeds the budget\n")
        self.assertEqual(next_cursor, 49)
        self.assertEqual(end_line, 1)

    def test_no_trailing_newline(self):
        """File without trailing newline is handled correctly."""
        from tools.read_file import extract_content_by_cursor

        content = "Line 1\nLine 2\nLine 3"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 1000)
        )
        self.assertEqual(extracted, content)
        self.assertEqual(total_lines, 3)

    def test_sequential_reads_cover_all_content(self):
        """Sequential cursor reads cover the entire file without gaps."""
        from tools.read_file import extract_content_by_cursor

        lines = [f"Line {i:03d}: " + "X" * 90 + "\n" for i in range(20)]
        content = "".join(lines)
        budget = 500  # ~5 lines per read

        all_extracted = []
        cursor = 0
        reads = 0
        max_reads = 100

        while cursor < len(content) and reads < max_reads:
            extracted, next_cursor, start_line, end_line, total_lines = (
                extract_content_by_cursor(content, cursor, budget)
            )
            self.assertGreater(next_cursor, cursor, "Cursor must advance")
            all_extracted.append(extracted)
            cursor = next_cursor
            reads += 1

        # All content should be covered
        reassembled = "".join(all_extracted)
        self.assertEqual(reassembled, content)

    def test_with_line_numbers(self):
        """Line numbers are included and budget-accounted."""
        from tools.read_file import extract_content_by_cursor

        content = "AAAA\nBBBB\nCCCC\n"
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 1000, show_line_numbers=True)
        )
        self.assertIn("1→AAAA", extracted)
        self.assertIn("2→BBBB", extracted)
        self.assertIn("3→CCCC", extracted)

    def test_line_numbers_affect_budget(self):
        """Line number prefixes are counted against the budget."""
        from tools.read_file import extract_content_by_cursor

        # Each line with prefix: "1→AAAA" = 6 chars, "2→BBBB" = 6 chars + 1 newline each = 7
        content = "AAAA\nBBBB\nCCCC\n"
        # Budget of 8 should fit "1→AAAA\n" (7 chars) but not "2→BBBB\n" (7 more)
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 0, 8, show_line_numbers=True)
        )
        self.assertIn("1→AAAA", extracted)
        self.assertNotIn("2→BBBB", extracted)
        self.assertEqual(end_line, 1)
        # Cursor advances by the RAW line length (5 chars for "AAAA\n")
        self.assertEqual(next_cursor, 5)

    def test_line_numbers_resume_correctly(self):
        """Line numbers are correct when resuming from a cursor."""
        from tools.read_file import extract_content_by_cursor

        content = "AAAA\nBBBB\nCCCC\n"
        # Start from line 2 (cursor=5, after "AAAA\n")
        extracted, next_cursor, start_line, end_line, total_lines = (
            extract_content_by_cursor(content, 5, 1000, show_line_numbers=True)
        )
        self.assertIn("2→BBBB", extracted)
        self.assertIn("3→CCCC", extracted)
        self.assertNotIn("1→", extracted)


class TestReadFileCursorPagination(unittest.TestCase):
    """Integration tests for read_file with cursor-based pagination."""

    def _patch_limit(self, limit_value):
        """Return a context manager that patches READ_CHAR_LIMIT in the read_file module."""
        return patch("tools.read_file.READ_CHAR_LIMIT", limit_value)

    def test_auto_pagination_large_file(self):
        """Large file auto-paginates and includes cursor in continuation."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            with self._patch_limit(2000):
                result = run_async(read_file("large.txt"))

                self.assertIn("chars 0-", result)
                self.assertIn("reads remaining", result)
                self.assertIn("cursor=", result)
                self.assertIn("To continue reading", result)

            session.clear()

    def test_explicit_cursor_request(self):
        """Explicit cursor continues from correct position."""
        import re

        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            with self._patch_limit(2000):
                # First read to get cursor
                result1 = run_async(read_file("large.txt"))
                self.assertIn("cursor=", result1)

                # Extract cursor value from result
                cursor_match = re.search(r'cursor=(\d+)', result1)
                self.assertIsNotNone(cursor_match)
                cursor_value = int(cursor_match.group(1))

                # Second read with cursor
                result2 = run_async(read_file("large.txt", cursor=cursor_value))
                self.assertIn(f"chars {cursor_value}-", result2)
                self.assertIn("File: large.txt", result2)

            session.clear()

    def test_cursor_beyond_eof(self):
        """Cursor beyond file content returns EOF message."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            ws.create_file("test.txt", "Hello\n")

            result = run_async(read_file("test.txt", cursor=99999))
            self.assertIn("End of file reached", result)
            session.clear()

    def test_cursor_with_offset_error(self):
        """Using cursor with offset returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", cursor=0, offset=5))
            self.assertIn("Error", result)
            self.assertIn("Cannot use 'cursor' with 'offset'", result)
            session.clear()

    def test_cursor_with_limit_error(self):
        """Using cursor with limit returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", cursor=0, limit=10))
            self.assertIn("Error", result)
            self.assertIn("Cannot use 'cursor' with 'offset'", result)
            session.clear()

    def test_negative_cursor_error(self):
        """Negative cursor returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", cursor=-1))
            self.assertIn("Error", result)
            self.assertIn("must be non-negative", result)
            session.clear()

    def test_cursor_with_line_numbers(self):
        """Cursor pagination works with show_line_numbers."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            with self._patch_limit(2000):
                result = run_async(
                    read_file("large.txt", cursor=0, show_line_numbers=True)
                )
                self.assertIn("→", result)  # Line number separator
                self.assertIn("cursor=", result)

            session.clear()

    def test_small_file_no_pagination(self):
        """Small files under limit return full content without pagination."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            ws.create_file("small.txt", "Small content\n")

            with self._patch_limit(50000):
                result = run_async(read_file("small.txt"))
                self.assertNotIn("cursor=", result)  # No pagination
                self.assertIn("Small content", result)

            session.clear()

    def test_sequential_reads_cover_full_file(self):
        """Sequential cursor-based reads cover the entire file content."""
        import re

        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            lines = [f"Line {i:03d}: " + "Y" * 90 + "\n" for i in range(50)]
            ws.create_file("big.txt", "".join(lines))

            with self._patch_limit(2000):
                collected_lines = []
                cursor = None
                max_iterations = 100
                iterations = 0

                while iterations < max_iterations:
                    if cursor is None:
                        result = run_async(read_file("big.txt"))
                    else:
                        result = run_async(read_file("big.txt", cursor=cursor))

                    # Collect actual file lines from result (skip headers/footers)
                    for line in result.split("\n"):
                        if line.startswith("Line ") and "Y" in line:
                            collected_lines.append(line + "\n")

                    # Check for continuation
                    cursor_match = re.search(r'cursor=(\d+)', result)
                    if cursor_match:
                        cursor = int(cursor_match.group(1))
                    else:
                        break
                    iterations += 1

                # All lines should be present
                self.assertEqual(len(collected_lines), 50)
                # Check first and last
                self.assertTrue(collected_lines[0].startswith("Line 000:"))
                self.assertTrue(collected_lines[49].startswith("Line 049:"))

            session.clear()

    def test_overhead_included_in_budget(self):
        """Instruction files are included and accounted for in the budget."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a subdirectory with an AGENTS.md
            ws.create_dir("src")
            agents_content = "# Agent Instructions\n" + "Important info. " * 100
            ws.create_file("src/AGENTS.md", agents_content)

            # Create a large file in that directory
            lines = [f"Line {i:03d}: " + "Z" * 90 + "\n" for i in range(50)]
            ws.create_file("src/big.py", "".join(lines))

            with self._patch_limit(3000):
                result = run_async(read_file("src/big.py"))

                # Should include AGENTS.md content
                self.assertIn("Agent Instructions", result)
                # Should still have cursor pagination
                self.assertIn("cursor=", result)
                # The instruction content should be there
                self.assertIn("Important info", result)

                # Total output should be reasonable relative to limit
                # (may exceed slightly due to at-least-one-line guarantee)
                # but should not be wildly over
                self.assertLess(len(result), 3000 * 2)

            session.clear()

    def test_eof_reached_message(self):
        """Last read shows end of file message."""
        import re

        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            lines = [f"Line {i:02d}\n" for i in range(10)]
            ws.create_file("small_paged.txt", "".join(lines))

            with self._patch_limit(30):
                cursor = None
                last_result = ""
                for _ in range(100):
                    if cursor is None:
                        result = run_async(read_file("small_paged.txt"))
                    else:
                        result = run_async(read_file("small_paged.txt", cursor=cursor))

                    last_result = result
                    cursor_match = re.search(r'cursor=(\d+)', result)
                    if not cursor_match:
                        break
                    cursor = int(cursor_match.group(1))

                self.assertIn("End of file reached", last_result)

            session.clear()


class TestConfigLoader(unittest.TestCase):
    """Test the configuration loader."""

    def test_default_value(self):
        """Default is 50000 when config missing."""
        from config import DEFAULT_READ_CHAR_LIMIT

        self.assertEqual(DEFAULT_READ_CHAR_LIMIT, 50000)

    def test_load_from_config(self):
        """Load custom value from appsettings.json."""
        from config import load_read_char_limit

        with TempWorkspace() as ws:
            config_file = ws.path / "appsettings.json"
            config_file.write_text('{"readCharLimit": 25000}', encoding="utf-8")

            result = load_read_char_limit(ws.path)
            self.assertEqual(result, 25000)

    def test_invalid_value_uses_default(self):
        """Invalid values fall back to default."""
        from config import load_read_char_limit, DEFAULT_READ_CHAR_LIMIT

        with TempWorkspace() as ws:
            config_file = ws.path / "appsettings.json"
            config_file.write_text('{"readCharLimit": -100}', encoding="utf-8")

            result = load_read_char_limit(ws.path)
            self.assertEqual(result, DEFAULT_READ_CHAR_LIMIT)

    def test_zero_value_uses_default(self):
        """Zero value falls back to default."""
        from config import load_read_char_limit, DEFAULT_READ_CHAR_LIMIT

        with TempWorkspace() as ws:
            config_file = ws.path / "appsettings.json"
            config_file.write_text('{"readCharLimit": 0}', encoding="utf-8")

            result = load_read_char_limit(ws.path)
            self.assertEqual(result, DEFAULT_READ_CHAR_LIMIT)

    def test_missing_config_uses_default(self):
        """Missing config file uses default."""
        from config import load_read_char_limit, DEFAULT_READ_CHAR_LIMIT

        with TempWorkspace() as ws:
            result = load_read_char_limit(ws.path)
            self.assertEqual(result, DEFAULT_READ_CHAR_LIMIT)


class TestReadCharLimitParameter(unittest.TestCase):
    """Tests that read_file respects the read_char_limit parameter."""

    def test_explicit_limit_triggers_pagination(self):
        """Passing a small read_char_limit forces pagination on a normal-sized file."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a file that is larger than the limit we'll pass
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("test.txt", "".join(lines))

            # Pass a small limit directly (no patching needed)
            result = run_async(read_file("test.txt", read_char_limit=2000))

            self.assertIn("chars 0-", result)
            self.assertIn("reads remaining", result)
            self.assertIn("cursor=", result)

            session.clear()

    def test_explicit_limit_does_not_paginate_small_file(self):
        """Large explicit limit doesn't paginate a small file."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            ws.create_file("small.txt", "Hello World\n")

            result = run_async(read_file("small.txt", read_char_limit=50000))

            self.assertNotIn("cursor=", result)
            self.assertIn("Hello World", result)

            session.clear()

    def test_none_limit_falls_back_to_global(self):
        """read_char_limit=None falls back to module-level READ_CHAR_LIMIT."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a file just under the global limit (50000 by default)
            ws.create_file("medium.txt", "A" * 100 + "\n")

            # None means use global limit; file is tiny so no pagination
            result = run_async(read_file("medium.txt", read_char_limit=None))

            self.assertNotIn("cursor=", result)
            self.assertIn("A" * 100, result)

            session.clear()


if __name__ == "__main__":
    unittest.main()
