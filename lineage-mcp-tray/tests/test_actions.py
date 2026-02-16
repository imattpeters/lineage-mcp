"""Tests for actions module."""

from unittest.mock import MagicMock

from lineage_tray.actions import clear_cache, interrupt, resume
from lineage_tray.session_store import SessionInfo

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
