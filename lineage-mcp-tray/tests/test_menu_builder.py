"""Tests for menu_builder module."""

import time
from unittest.mock import MagicMock

import pystray

from lineage_tray.menu_builder import _shorten_path, build_menu
from lineage_tray.session_store import SessionStore


class TestBuildMenu:
    """Tests for build_menu function."""

    def test_empty_sessions(self):
        store = SessionStore()
        mock_server = MagicMock()
        mock_icon = MagicMock()
        items = build_menu(store, mock_server, mock_icon)
        # Should have "No active sessions" + separator + Quit
        texts = [item.text for item in items if hasattr(item, "text") and item.text]
        assert "No active sessions" in texts
        assert "Quit" in texts

    def test_single_session(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj",
            "started_at": time.time(),
            "client_name": "VS Code",
            "files_tracked": 5,
        })
        mock_server = MagicMock()
        mock_icon = MagicMock()
        items = build_menu(store, mock_server, mock_icon)
        texts = [item.text for item in items if hasattr(item, "text") and item.text]
        # Should contain the base_dir header and session display name
        assert any("C:\\proj" in t for t in texts)
        assert any("VS Code" in t for t in texts)
        assert "Quit" in texts

    def test_multiple_groups(self):
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
            "client_name": "Cursor",
        })
        mock_server = MagicMock()
        mock_icon = MagicMock()
        items = build_menu(store, mock_server, mock_icon)
        texts = [item.text for item in items if hasattr(item, "text") and item.text]
        assert any("C:\\proj1" in t for t in texts)
        assert any("C:\\proj2" in t for t in texts)


class TestShortenPath:
    """Tests for _shorten_path function."""

    def test_short_path_unchanged(self):
        assert _shorten_path("C:\\proj") == "C:\\proj"

    def test_long_path_shortened(self):
        long_path = "C:\\Users\\username\\Documents\\projects\\very-long-project-name\\subdir"
        result = _shorten_path(long_path, max_len=30)
        assert len(result) < len(long_path)
        assert "..." in result
