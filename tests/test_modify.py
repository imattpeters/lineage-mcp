"""Tests for tools/modify.py module."""

import sys
import unittest
from pathlib import Path

_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace, run_async


class TestModifyBasic(unittest.TestCase):
    def test_create_file(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "hello",
                }
            ]))

            self.assertIn("Successfully created", result)
            self.assertEqual((ws.path / "new.txt").read_text(), "hello")
            session.clear()

    def test_create_existing_file_fails(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            ws.create_file("new.txt", "hello")

            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "world",
                }
            ]))

            self.assertIn("Error", result)
            self.assertIn("already exists", result)
            session.clear()

    def test_overwrite_file(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("config.txt", "old")

            result = run_async(modify([
                {
                    "file_path": "config.txt",
                    "operation": "overwrite",
                    "text": "new",
                }
            ]))

            self.assertIn("Successfully overwrote", result)
            self.assertEqual(file_path.read_text(), "new")
            session.clear()

    def test_overwrite_missing_file_creates_it(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()

            result = run_async(modify([
                {
                    "file_path": "nested/config.txt",
                    "operation": "overwrite",
                    "text": "new",
                }
            ]))

            self.assertIn("Successfully overwrote", result)
            self.assertEqual((ws.path / "nested" / "config.txt").read_text(), "new")
            session.clear()

    def test_append_file(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("log.txt", "a")

            result = run_async(modify([
                {
                    "file_path": "log.txt",
                    "operation": "append",
                    "text": "b",
                }
            ]))

            self.assertIn("Successfully appended", result)
            self.assertEqual(file_path.read_text(), "ab")
            session.clear()

    def test_append_missing_file_fails(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()

            result = run_async(modify([
                {
                    "file_path": "missing.txt",
                    "operation": "append",
                    "text": "b",
                }
            ]))

            self.assertIn("Error", result)
            self.assertIn("File not found", result)
            session.clear()

    def test_replace_one_match(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("test.txt", "Hello, World!")

            result = run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "match_text": "World",
                    "text": "Python",
                }
            ]))

            self.assertIn("Successfully replaced 1 occurrence", result)
            self.assertEqual(file_path.read_text(), "Hello, Python!")
            session.clear()

    def test_replace_all_matches(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("test.txt", "foo foo foo")

            result = run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "match_text": "foo",
                    "text": "bar",
                    "occurrence": "all",
                }
            ]))

            self.assertIn("Successfully replaced 3 occurrence", result)
            self.assertEqual(file_path.read_text(), "bar bar bar")
            session.clear()


class TestModifyValidation(unittest.TestCase):
    def test_empty_operations_fail(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([]))
            self.assertIn("No operations", result)
            session.clear()

    def test_invalid_on_error_fails(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "hello",
                }
            ], on_error="stop"))
            self.assertIn("on_error", result)
            session.clear()

    def test_missing_file_path(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "operation": "create",
                    "text": "hello",
                }
            ]))
            self.assertIn("missing 'file_path'", result)
            session.clear()

    def test_missing_operation(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "text": "hello",
                }
            ]))
            self.assertIn("invalid 'operation'", result)
            session.clear()

    def test_missing_text(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                }
            ]))
            self.assertIn("missing 'text'", result)
            session.clear()

    def test_replace_missing_match_text(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            ws.create_file("test.txt", "hello")
            result = run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "text": "changed",
                }
            ]))
            self.assertIn("missing 'match_text'", result)
            session.clear()

    def test_invalid_occurrence(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            ws.create_file("test.txt", "hello")
            result = run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "match_text": "hello",
                    "text": "changed",
                    "occurrence": "many",
                }
            ]))
            self.assertIn("invalid 'occurrence'", result)
            session.clear()

    def test_match_text_for_non_replace_fails(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "hello",
                    "match_text": "x",
                }
            ]))
            self.assertIn("only valid for replace", result)
            session.clear()

    def test_occurrence_for_non_replace_fails(self) -> None:
        with TempWorkspace():
            from session_state import session
            from tools.modify import modify

            session.clear()
            result = run_async(modify([
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "hello",
                    "occurrence": "all",
                }
            ]))
            self.assertIn("only valid for replace", result)
            session.clear()


class TestModifyBatchBehavior(unittest.TestCase):
    def test_mixed_batch_across_multiple_files(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            ws.create_file("b.txt", "old")
            ws.create_file("c.txt", "before")

            result = run_async(modify([
                {
                    "file_path": "a.txt",
                    "operation": "create",
                    "text": "hello",
                },
                {
                    "file_path": "b.txt",
                    "operation": "overwrite",
                    "text": "new",
                },
                {
                    "file_path": "c.txt",
                    "operation": "append",
                    "text": " after",
                },
            ]))

            self.assertIn("Operation 1", result)
            self.assertIn("Operation 2", result)
            self.assertIn("Operation 3", result)
            self.assertEqual((ws.path / "a.txt").read_text(), "hello")
            self.assertEqual((ws.path / "b.txt").read_text(), "new")
            self.assertEqual((ws.path / "c.txt").read_text(), "before after")
            session.clear()

    def test_multiple_operations_same_file_are_ordered(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("app.py", "DEBUG = True")

            result = run_async(modify([
                {
                    "file_path": "app.py",
                    "operation": "replace",
                    "match_text": "DEBUG = True",
                    "text": "DEBUG = False",
                },
                {
                    "file_path": "app.py",
                    "operation": "append",
                    "text": "\nprint('done')\n",
                },
            ]))

            self.assertIn("Operation 1", result)
            self.assertIn("Operation 2", result)
            self.assertEqual(file_path.read_text(), "DEBUG = False\nprint('done')\n")
            session.clear()

    def test_abort_stops_later_operations(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("a.txt", "hello")

            result = run_async(modify([
                {
                    "file_path": "a.txt",
                    "operation": "replace",
                    "match_text": "hello",
                    "text": "changed",
                },
                {
                    "file_path": "missing.txt",
                    "operation": "append",
                    "text": "x",
                },
                {
                    "file_path": "a.txt",
                    "operation": "append",
                    "text": "!",
                },
            ], on_error="abort"))

            self.assertIn("Operation 1", result)
            self.assertIn("Operation 2", result)
            self.assertNotIn("Operation 3", result)
            self.assertEqual(file_path.read_text(), "changed")
            session.clear()

    def test_continue_keeps_going_after_failure(self) -> None:
        with TempWorkspace() as ws:
            from session_state import session
            from tools.modify import modify

            session.clear()
            file_path = ws.create_file("a.txt", "hello")

            result = run_async(modify([
                {
                    "file_path": "missing.txt",
                    "operation": "append",
                    "text": "x",
                },
                {
                    "file_path": "a.txt",
                    "operation": "append",
                    "text": "!",
                },
            ], on_error="continue"))

            self.assertIn("Operation 1", result)
            self.assertIn("Operation 2", result)
            self.assertEqual(file_path.read_text(), "hello!")
            session.clear()


class TestModifyCacheBehavior(unittest.TestCase):
    def test_successful_writes_update_cache(self) -> None:
        with TempWorkspace() as ws:
            from file_watcher import get_changed_files
            from session_state import session
            from tools.modify import modify

            session.clear()
            ws.create_file("test.txt", "Hello")

            run_async(modify([
                {
                    "file_path": "test.txt",
                    "operation": "replace",
                    "match_text": "Hello",
                    "text": "Changed",
                },
                {
                    "file_path": "new.txt",
                    "operation": "create",
                    "text": "content",
                },
            ]))

            changed = get_changed_files()
            self.assertEqual(len(changed), 0)
            session.clear()


if __name__ == "__main__":
    unittest.main()
