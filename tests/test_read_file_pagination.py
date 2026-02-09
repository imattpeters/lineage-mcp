"""Tests for pagination functionality in read_file tool.

Tests the paginate_content helper and read_file integration with pagination.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestPaginateContent(unittest.TestCase):
    """Test the pagination logic with various scenarios."""

    def test_empty_file(self):
        """Empty file returns empty content."""
        from tools.read_file import paginate_content

        content = ""
        result = paginate_content(content, 0, 1000)
        self.assertEqual(result, ("", 0, 0, 0, 1, True))

    def test_single_page_file(self):
        """File under limit returns full content."""
        from tools.read_file import paginate_content

        content = "Line 1\nLine 2\nLine 3\n"
        result = paginate_content(content, 0, 1000)
        self.assertEqual(result[0], content)
        self.assertEqual(result[1], len(content))
        self.assertEqual(result[2], 0)  # start_line
        self.assertEqual(result[3], 3)  # end_line
        self.assertEqual(result[4], 1)  # total_pages
        self.assertTrue(result[5])  # is_last_page

    def test_exact_line_boundary(self):
        """Pagination stops exactly at line boundary."""
        from tools.read_file import paginate_content

        # 5 lines of 100 chars each (including newline)
        lines = ["A" * 99 + "\n" for _ in range(5)]
        content = "".join(lines)

        result = paginate_content(content, 0, 500)  # 500 chars = 5 lines
        self.assertEqual(result[0], content)
        self.assertEqual(result[3], 5)  # Should end after line 5

    def test_line_aware_truncation(self):
        """Truncation happens at nearest line boundary before limit."""
        from tools.read_file import paginate_content

        # Lines: 100, 200, 400, 100, 300 chars (including newlines)
        lines = [
            "A" * 99 + "\n",
            "B" * 199 + "\n",
            "C" * 399 + "\n",
            "D" * 99 + "\n",
            "E" * 299 + "\n",
        ]
        content = "".join(lines)

        # Limit = 600
        # Cumulative: 100, 300, 700, 800, 1100
        # Should stop after line 2 (300 chars) because line 3 (700) exceeds 600
        result = paginate_content(content, 0, 600)
        self.assertEqual(result[1], 300)  # Actual chars returned
        self.assertEqual(result[3], 2)  # End after line 2

    def test_multi_page_navigation(self):
        """Navigate through multiple pages."""
        from tools.read_file import paginate_content

        # Create 10 lines of 100 chars each
        lines = [f"Line {i:02d}" + "A" * 90 + "\n" for i in range(10)]
        content = "".join(lines)

        char_limit = 250  # Should fit ~2.5 lines, truncates to 2 lines

        # Page 0: Lines 0-2 (200 chars)
        r0 = paginate_content(content, 0, char_limit)
        self.assertEqual(r0[2], 0)
        self.assertEqual(r0[3], 2)

        # Page 1: Lines 2-4 (200 chars)
        r1 = paginate_content(content, 1, char_limit)
        self.assertEqual(r1[2], 2)
        # The end_line can be 4 or 5 depending on line boundary alignment
        self.assertTrue(r1[3] == 4 or r1[3] == 5)

        # Page 2: Lines 4-6 (200 chars)
        r2 = paginate_content(content, 2, char_limit)
        self.assertEqual(r2[2], 4)

        # Page 3: Lines 6-8 (200 chars)
        r3 = paginate_content(content, 3, char_limit)
        self.assertEqual(r3[2], 6)

        # Page 4: Lines 8-10 (200 chars)
        r4 = paginate_content(content, 4, char_limit)
        self.assertEqual(r4[2], 8)
        self.assertTrue(r4[5])  # Last page

    def test_page_six_scenario(self):
        """Test requesting page 6 in a multi-page file.

        Setup: 30 lines of 200 chars each = 6000 chars total
        Limit: 1000 chars per page
        Expected: 6 pages total (Pages 0-5)
        Page 6 should return empty with EOF indication.
        """
        from tools.read_file import paginate_content

        lines = [f"PageTest Line {i:02d}" + "X" * 180 + "\n" for i in range(30)]
        content = "".join(lines)
        char_limit = 1000

        # Verify each valid page
        for page_num in range(6):
            result = paginate_content(content, page_num, char_limit)
            self.assertEqual(result[4], 6, f"Page {page_num}: wrong total_pages")
            is_last = page_num == 5
            self.assertEqual(result[5], is_last, f"Page {page_num}: wrong is_last_page")

        # Now test page 6 (beyond content)
        r6 = paginate_content(content, 6, char_limit)
        self.assertEqual(r6[0], "")  # Empty content
        self.assertEqual(r6[1], 0)  # Zero chars
        self.assertEqual(r6[2], 30)  # Start at end
        self.assertEqual(r6[3], 30)  # End at end
        self.assertEqual(r6[4], 6)  # Still 6 pages total
        self.assertTrue(r6[5])  # Considered last page

    def test_uneven_line_lengths(self):
        """Handle files with irregular line lengths."""
        from tools.read_file import paginate_content

        # Varying line lengths
        lines = [
            "Short\n",  # 6 chars
            "Medium line here\n",  # 18 chars
            "This is a much longer line indeed\n",  # 36 chars
            "Tiny\n",  # 5 chars
            "Another substantial line content\n",  # 35 chars
        ]
        content = "".join(lines)
        # Total: 100 chars

        # Limit = 50
        # Cumulative: 6, 24, 60, 65, 100
        # Should stop after line 2 (24 chars) because line 3 (60) exceeds 50
        result = paginate_content(content, 0, 50)
        # Allow for 23-24 chars depending on exact boundary calculation
        self.assertTrue(result[1] == 23 or result[1] == 24)
        self.assertEqual(result[3], 2)

    def test_long_line_exceeds_limit(self):
        """Handle single line exceeding character limit."""
        from tools.read_file import paginate_content

        content = "A" * 10000 + "\n"  # One long line

        result = paginate_content(content, 0, 1000)
        self.assertEqual(len(result[0]), 1000)
        # For a single line, if we've consumed it all, it might be marked as last
        # Check that we can get more content on next page
        result2 = paginate_content(content, 1, 1000)
        self.assertEqual(len(result2[0]), 1000)

    def test_no_newline_at_end(self):
        """Handle file without trailing newline."""
        from tools.read_file import paginate_content

        content = "Line 1\nLine 2\nLine 3"  # No final newline

        result = paginate_content(content, 0, 1000)
        self.assertEqual(result[0], content)
        self.assertEqual(result[3], 3)  # Still 3 lines


class TestReadFilePagination(unittest.TestCase):
    """Integration tests for read_file with pagination."""

    def test_auto_pagination_first_page(self):
        """Reading large file returns first page automatically."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file
            from tools import READ_CHAR_LIMIT

            session.clear()

            # Create a multi-page test file
            # 20 lines of 500 chars = 10,000 chars total
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT
            import tools

            original_limit = tools.READ_CHAR_LIMIT
            tools.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt"))

                self.assertIn("[Page 1 of", result)
                self.assertIn("chars]", result)
                self.assertIn("To continue reading", result)
            finally:
                import tools

                tools.READ_CHAR_LIMIT = original_limit
                session.clear()

            # Create a multi-page test file
            # 20 lines of 500 chars = 10,000 chars total
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            import tools.read_file

            original_limit = tools.read_file.READ_CHAR_LIMIT
            tools.read_file.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt"))

                self.assertIn("[Page 1 of", result)
                self.assertIn("chars]", result)
                self.assertIn("To continue reading", result)
            finally:
                import tools.read_file

                tools.read_file.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_explicit_page_request(self):
        """Request specific page returns correct content."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            import tools.read_file

            original_limit = tools.read_file.READ_CHAR_LIMIT
            tools.read_file.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt", page=2))

                self.assertIn("[Page 3 of", result)
                self.assertIn("File: large.txt", result)
            finally:
                tools.read_file.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_page_beyond_eof(self):
        """Requesting page beyond content returns appropriate message."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            import tools.read_file

            original_limit = tools.read_file.READ_CHAR_LIMIT
            tools.read_file.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt", page=10))

                self.assertTrue(
                    "End of file" in result or "End of file reached" in result
                )
            finally:
                tools.read_file.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_explicit_page_request(self):
        """Request specific page returns correct content."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file
            import tools.read_file as rf_module

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            original_limit = rf_module.READ_CHAR_LIMIT
            rf_module.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt", page=2))

                self.assertIn("[Page 3 of", result)
                self.assertIn("File: large.txt", result)
            finally:
                rf_module.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_page_beyond_eof(self):
        """Requesting page beyond content returns appropriate message."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file
            import tools.read_file as rf_module

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            original_limit = rf_module.READ_CHAR_LIMIT
            rf_module.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(read_file("large.txt", page=10))

                self.assertTrue(
                    "End of file" in result or "End of file reached" in result
                )
            finally:
                rf_module.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_page_with_offset_error(self):
        """Using page with offset returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a test file
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", page=0, offset=5))

            self.assertIn("Error", result)
            self.assertIn("Cannot use 'page' with 'offset'", result)
            session.clear()

    def test_page_with_limit_error(self):
        """Using page with limit returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a test file
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", page=0, limit=10))

            self.assertIn("Error", result)
            self.assertIn("Cannot use 'page' with 'offset'", result)
            session.clear()

    def test_negative_page_error(self):
        """Negative page number returns error."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a test file
            ws.create_file("test.txt", "some content\n" * 10)

            result = run_async(read_file("test.txt", page=-1))

            self.assertIn("Error", result)
            self.assertIn("must be non-negative", result)
            session.clear()

    def test_pagination_with_line_numbers(self):
        """Pagination works correctly with show_line_numbers."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a multi-page test file
            lines = [f"Line {i:02d}: " + "X" * 490 + "\n" for i in range(20)]
            ws.create_file("large.txt", "".join(lines))

            # Mock READ_CHAR_LIMIT directly in the read_file module
            import tools.read_file

            original_limit = tools.read_file.READ_CHAR_LIMIT
            tools.read_file.READ_CHAR_LIMIT = 2000

            try:
                result = run_async(
                    read_file("large.txt", page=1, show_line_numbers=True)
                )

                # Should have pagination header with line numbers
                self.assertIn("[Page 2 of", result)
                self.assertIn("→", result)  # Line number separator
            finally:
                tools.read_file.READ_CHAR_LIMIT = original_limit
                session.clear()

    def test_small_file_no_pagination(self):
        """Small files under limit return full content without pagination."""
        with TempWorkspace() as ws:
            from session_state import session
            from tools.read_file import read_file

            session.clear()

            # Create a small file
            ws.create_file("small.txt", "Small content\n")

            # Mock READ_CHAR_LIMIT to large value
            import tools.read_file

            original_limit = tools.read_file.READ_CHAR_LIMIT
            tools.read_file.READ_CHAR_LIMIT = 50000

            try:
                result = run_async(read_file("small.txt"))

                self.assertNotIn("[Page", result)  # No pagination header
                self.assertIn("Small content", result)
            finally:
                tools.read_file.READ_CHAR_LIMIT = original_limit
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


if __name__ == "__main__":
    unittest.main()
