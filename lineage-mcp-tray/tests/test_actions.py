"""Tests for actions module."""

from unittest.mock import MagicMock

from lineage_tray.actions import clear_cache, clear_by_filter, interrupt, resume
from lineage_tray.session_store import SessionInfo, SessionStore

import time


class TestActions:
    """Tests for tray menu actions."""

    def test_clear_cache_sends_message(self):
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True
        session = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        result = clear_cache(mock_server, session)
        mock_server.send_to_session.assert_called_once_with(
            "s1", {"type": "clear_cache"}
        )
        assert result is True

    def test_interrupt_sends_message(self):
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True
        session = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        result = interrupt(mock_server, session)
        mock_server.send_to_session.assert_called_once_with(
            "s1", {"type": "interrupt"}
        )
        assert result is True

    def test_clear_cache_handles_failure(self):
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = False
        session = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        result = clear_cache(mock_server, session)
        assert result is False

    def test_resume_sends_message(self):
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True
        session = SessionInfo(
            session_id="s1",
            pid=1234,
            base_dir="C:\\proj",
            started_at=time.time(),
        )
        result = resume(mock_server, session)
        mock_server.send_to_session.assert_called_once_with(
            "s1", {"type": "resume"}
        )
        assert result is True


class TestClearByFilter:
    """Tests for clear_by_filter action."""

    def test_clear_by_filter_broadcasts(self):
        """Action sends clear_cache to all matching sessions."""
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True

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
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "VS Code",
        })
        store.register({
            "session_id": "s3",
            "pid": 9012,
            "base_dir": "C:\\proj2",
            "started_at": time.time(),
            "client_name": "VS Code",
        })

        result = clear_by_filter(store, mock_server, base_dir="C:\\proj1")
        assert result["sessions_cleared"] == 2
        assert mock_server.send_to_session.call_count == 2

    def test_clear_by_filter_no_matches(self):
        """Returns 0 when no sessions match."""
        mock_server = MagicMock()
        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
        })

        result = clear_by_filter(store, mock_server, base_dir="C:\\nonexistent")
        assert result["sessions_cleared"] == 0
        mock_server.send_to_session.assert_not_called()

    def test_clear_by_filter_handles_send_failure(self):
        """Counts only successful sends."""
        mock_server = MagicMock()
        mock_server.send_to_session.side_effect = [True, False]

        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 1234,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
        })
        store.register({
            "session_id": "s2",
            "pid": 5678,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
        })

        result = clear_by_filter(store, mock_server, base_dir="C:\\proj1")
        assert result["sessions_cleared"] == 1

    def test_clear_by_filter_with_ancestor_pids(self):
        """Clears only the session with matching ancestor PIDs."""
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True

        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "claude-code",
            "ancestor_pids": [100, 200, 300],
        })
        store.register({
            "session_id": "s2",
            "pid": 101,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "claude-code",
            "ancestor_pids": [101, 400, 500],
        })

        # Only s1 shares ancestor 200
        result = clear_by_filter(
            store, mock_server,
            base_dir="C:\\proj1",
            client_name="claude-code",
            ancestor_pids=[600, 200, 700],
        )
        assert result["sessions_cleared"] == 1
        mock_server.send_to_session.assert_called_once_with(
            "s1", {"type": "clear_cache"}
        )

    def test_clear_by_filter_ancestor_fallback_to_client_name(self):
        """Falls back to client_name when session has no ancestor_pids."""
        mock_server = MagicMock()
        mock_server.send_to_session.return_value = True

        store = SessionStore()
        store.register({
            "session_id": "s1",
            "pid": 100,
            "base_dir": "C:\\proj1",
            "started_at": time.time(),
            "client_name": "claude-code",
            # No ancestor_pids
        })

        result = clear_by_filter(
            store, mock_server,
            base_dir="C:\\proj1",
            client_name="claude",
            ancestor_pids=[400, 500],
        )
        assert result["sessions_cleared"] == 1
