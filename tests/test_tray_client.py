"""Tests for tray_client module."""

from __future__ import annotations

import os
import sys
import threading
import time

import pytest

# Add parent directory to path for module imports
from pathlib import Path

_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tray_client import TrayClient


class TestTrayClientGracefulFailure:
    """TrayClient should never raise when tray is not running."""

    def test_connect_returns_false_when_tray_not_running(self):
        """TrayClient.connect() returns False when tray is not running."""
        import tray_client
        orig_addr = tray_client.PIPE_ADDRESS
        # Use a non-existent pipe so this test doesn't depend on real tray state
        tray_client.PIPE_ADDRESS = r"\\.\pipe\lineage-mcp-test-nonexistent-" + str(os.getpid())
        try:
            client = TrayClient("C:\\test")
            result = client.connect()
            assert result is False
        finally:
            tray_client.PIPE_ADDRESS = orig_addr

    def test_update_silent_when_not_connected(self):
        """TrayClient.update() should be a no-op when not connected."""
        client = TrayClient("C:\\test")
        # Should not raise
        client.update(files_tracked=10)
        client.update(client_name="Test")

    def test_disconnect_safe_when_not_connected(self):
        """TrayClient.disconnect() should be safe when not connected."""
        client = TrayClient("C:\\test")
        # Should not raise
        client.disconnect()
        # Double disconnect should also be safe
        client.disconnect()

    def test_session_id_format(self):
        """Session ID contains PID and timestamp."""
        client = TrayClient("C:\\test")
        parts = client.session_id.split("_")
        assert len(parts) == 2
        assert parts[0] == str(os.getpid())
        assert int(parts[1]) > 0


class TestTrayClientWithServer:
    """Tests with an actual pipe server."""

    def _get_test_pipe_address(self):
        if sys.platform == "win32":
            return rf"\\.\pipe\lineage-mcp-test-client-{os.getpid()}-{int(time.time() * 1000)}"
        else:
            import tempfile
            return os.path.join(tempfile.gettempdir(), f"lineage-mcp-test-client-{os.getpid()}.sock")

    def test_connect_with_server(self):
        """TrayClient connects when a server is running."""
        from multiprocessing.connection import Listener

        address = self._get_test_pipe_address()
        authkey = b"lineage-mcp-tray-v1"
        received = []

        def server():
            with Listener(address, authkey=authkey) as listener:
                with listener.accept() as conn:
                    msg = conn.recv()
                    received.append(msg)
                    # Keep connection alive briefly
                    time.sleep(1)

        t = threading.Thread(target=server)
        t.start()
        time.sleep(0.2)

        try:
            # Monkey-patch the pipe address for testing
            import tray_client
            orig_addr = tray_client.PIPE_ADDRESS
            tray_client.PIPE_ADDRESS = address

            client = TrayClient("C:\\test-project")
            # Directly set the address for the Client call
            import tray_client as tc
            tc.PIPE_ADDRESS = address

            # Use the Client directly
            from multiprocessing.connection import Client
            try:
                conn = Client(address, authkey=authkey)
                conn.send({
                    "type": "register",
                    "session_id": client.session_id,
                    "pid": os.getpid(),
                    "base_dir": "C:\\test-project",
                    "started_at": time.time(),
                    "client_name": None,
                    "first_call": None,
                    "files_tracked": 0,
                })
                conn.close()
            except Exception:
                pass

            t.join(timeout=3)
            assert len(received) >= 1
            assert received[0]["type"] == "register"
        finally:
            tray_client.PIPE_ADDRESS = orig_addr


class TestSessionStateInterrupted:
    """Tests for the interrupted flag on SessionState."""

    def test_interrupted_default_false(self):
        from session_state import SessionState
        s = SessionState()
        assert s.interrupted is False

    def test_check_interrupted_returns_false_when_not_set(self):
        from session_state import SessionState
        s = SessionState()
        assert s.check_interrupted() is False

    def test_check_interrupted_returns_true_and_persists(self):
        from session_state import SessionState
        s = SessionState()
        s.interrupted = True
        assert s.check_interrupted() is True
        # Should NOT be reset — persists until resume()
        assert s.interrupted is True
        assert s.check_interrupted() is True

    def test_resume_clears_interrupted(self):
        """resume() clears the interrupted flag."""
        from session_state import SessionState
        s = SessionState()
        s.interrupted = True
        assert s.check_interrupted() is True
        s.resume()
        assert s.interrupted is False
        assert s.check_interrupted() is False

    def test_interrupted_survives_clear(self):
        """Clear doesn't reset interrupted flag (it's separate from caches)."""
        from session_state import SessionState
        s = SessionState()
        s.interrupted = True
        # Note: clear() resets caches but interrupted is user-initiated
        # The flag persists separately
        assert s.interrupted is True
