"""Tests for lineage.py entrypoint normalization behavior."""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import run_async


class TestLineageReadNormalization(unittest.TestCase):
    """Tests for normalization of read() entrypoint arguments."""

    def test_blank_pagination_strings_are_treated_as_none(self) -> None:
        """Blank strings should be treated as omitted optional pagination args."""
        import lineage

        with patch.object(lineage, "read_file", new=AsyncMock(return_value="ok")) as read_file_mock:
            with patch.object(lineage, "get_read_char_limit", return_value=50000):
                with patch.object(lineage, "_append_footer", side_effect=lambda result, client_name=None: result):
                    result = run_async(
                        lineage.read(
                            "test.txt",
                            offset="",
                            limit="   ",
                            cursor="",
                        )
                    )

        self.assertEqual(result, "ok")
        read_file_mock.assert_awaited_once_with("test.txt", False, None, None, None, 50000)

    def test_zero_cursor_placeholder_is_dropped_for_line_pagination(self) -> None:
        """Cursor zero should be ignored when line-based pagination is otherwise specified."""
        import lineage

        with patch.object(lineage, "read_file", new=AsyncMock(return_value="ok")) as read_file_mock:
            with patch.object(lineage, "get_read_char_limit", return_value=50000):
                with patch.object(lineage, "_append_footer", side_effect=lambda result, client_name=None: result):
                    result = run_async(
                        lineage.read(
                            "test.txt",
                            offset=0,
                            limit=2,
                            cursor=0,
                        )
                    )

        self.assertEqual(result, "ok")
        read_file_mock.assert_awaited_once_with("test.txt", False, None, 2, None, 50000)

    def test_zero_line_placeholders_are_dropped_for_cursor_pagination(self) -> None:
        """Zero-valued line args should be ignored when a real cursor is provided."""
        import lineage

        with patch.object(lineage, "read_file", new=AsyncMock(return_value="ok")) as read_file_mock:
            with patch.object(lineage, "get_read_char_limit", return_value=50000):
                with patch.object(lineage, "_append_footer", side_effect=lambda result, client_name=None: result):
                    result = run_async(
                        lineage.read(
                            "test.txt",
                            offset=0,
                            limit=0,
                            cursor=12,
                        )
                    )

        self.assertEqual(result, "ok")
        read_file_mock.assert_awaited_once_with("test.txt", False, None, None, 12, 50000)

    def test_explicit_cursor_zero_is_preserved_without_conflict(self) -> None:
        """A standalone cursor of zero should remain valid and explicit."""
        import lineage

        with patch.object(lineage, "read_file", new=AsyncMock(return_value="ok")) as read_file_mock:
            with patch.object(lineage, "get_read_char_limit", return_value=50000):
                with patch.object(lineage, "_append_footer", side_effect=lambda result, client_name=None: result):
                    result = run_async(lineage.read("test.txt", cursor=0))

        self.assertEqual(result, "ok")
        read_file_mock.assert_awaited_once_with("test.txt", False, None, None, 0, 50000)


if __name__ == "__main__":
    unittest.main()