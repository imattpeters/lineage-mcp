"""Tests for tools/clear_cache.py module.

Tests the clear cache tool.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestClearCache(unittest.TestCase):
    """Tests for cache clearing."""

    def test_clear_cache_clears_all_caches(self) -> None:
        """Verify clear_cache clears all tracking."""
        with TempWorkspace():
            from session_state import session
            from tools.clear_cache import clear_cache

            # Track some files and folders
            session.track_file("/some/file.txt", 12345, "content")
            session.mark_folder_provided("/some/folder")

            result = run_async(clear_cache())

            # Should return success message
            self.assertIn("Cache cleared", result)

            # All caches should be cleared
            self.assertEqual(len(session.mtimes), 0)
            self.assertEqual(len(session.contents), 0)
            self.assertEqual(len(session.provided_folders), 0)

            session.clear()


if __name__ == "__main__":
    unittest.main()
