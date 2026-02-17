"""Tests for pipe_server module."""

import os
import sys
import threading
import time
from multiprocessing.connection import Client, Listener

import pytest


def _test_pipe_address():
    """Get a unique test pipe address."""
    if sys.platform == "win32":
        return rf"\\.\pipe\lineage-mcp-test-{os.getpid()}-{int(time.time() * 1000)}"
    else:
        import tempfile
        return os.path.join(tempfile.gettempdir(), f"lineage-mcp-test-{os.getpid()}.sock")


class TestPipeRoundtrip:
    """Integration tests for pipe communication."""

    def test_basic_roundtrip(self):
        """Test full message roundtrip: client → server → client."""
        address = _test_pipe_address()
        authkey = b"test"
        received = []

        def server():
            with Listener(address, authkey=authkey) as listener:
                with listener.accept() as conn:
                    msg = conn.recv()
                    received.append(msg)
                    conn.send({"type": "clear_cache"})

        t = threading.Thread(target=server)
        t.start()

        time.sleep(0.2)

        with Client(address, authkey=authkey) as conn:
            conn.send({
                "type": "register",
                "session_id": "test-1",
                "pid": os.getpid(),
                "base_dir": "C:\\test",
            })
            response = conn.recv()

        t.join(timeout=2)
        assert received[0]["type"] == "register"
        assert received[0]["session_id"] == "test-1"
        assert response["type"] == "clear_cache"

    def test_multiple_messages(self):
        """Test sending multiple messages over a pipe."""
        address = _test_pipe_address()
        authkey = b"test"
        received = []

        def server():
            with Listener(address, authkey=authkey) as listener:
                with listener.accept() as conn:
                    for _ in range(3):
                        msg = conn.recv()
                        received.append(msg)

        t = threading.Thread(target=server)
        t.start()

        time.sleep(0.2)

        with Client(address, authkey=authkey) as conn:
            conn.send({"type": "register", "session_id": "s1", "pid": 1, "base_dir": "C:\\a"})
            conn.send({"type": "update", "session_id": "s1", "files_tracked": 5})
            conn.send({"type": "unregister", "session_id": "s1"})

        t.join(timeout=2)
        assert len(received) == 3
        assert received[0]["type"] == "register"
        assert received[1]["type"] == "update"
        assert received[2]["type"] == "unregister"


class TestPipeServer:
    """Tests for PipeServer class."""

    def test_server_start_stop(self):
        """PipeServer can start and stop without error."""
        from lineage_tray.pipe_server import PipeServer

        address = _test_pipe_address()
        messages = []
        server = PipeServer(
            on_message=lambda sid, msg: messages.append((sid, msg)),
            address=address,
        )
        server.start()
        time.sleep(0.3)
        server.stop()

    def test_server_accepts_connection(self):
        """PipeServer accepts a client connection and routes messages."""
        from lineage_tray.pipe_server import PipeServer

        address = _test_pipe_address()
        messages = []
        event = threading.Event()

        def on_msg(sid, msg):
            messages.append((sid, msg))
            event.set()

        server = PipeServer(on_message=on_msg, address=address)
        server.start()

        time.sleep(0.3)

        try:
            conn = Client(address, authkey=b"lineage-mcp-tray-v1")
            conn.send({
                "type": "register",
                "session_id": "test-session",
                "pid": os.getpid(),
                "base_dir": "C:\\test",
                "started_at": time.time(),
            })

            event.wait(timeout=3)
            assert len(messages) >= 1
            assert messages[0][0] == "test-session"
            assert messages[0][1]["type"] == "register"

            conn.close()
        finally:
            server.stop()

    def test_server_send_to_session(self):
        """PipeServer can send messages back to connected sessions."""
        from lineage_tray.pipe_server import PipeServer

        address = _test_pipe_address()
        register_event = threading.Event()

        def on_msg(sid, msg):
            if msg.get("type") == "register":
                register_event.set()

        server = PipeServer(on_message=on_msg, address=address)
        server.start()

        time.sleep(0.3)

        try:
            conn = Client(address, authkey=b"lineage-mcp-tray-v1")
            conn.send({
                "type": "register",
                "session_id": "test-session",
                "pid": os.getpid(),
                "base_dir": "C:\\test",
                "started_at": time.time(),
            })

            register_event.wait(timeout=3)

            # Server sends back to the session
            result = server.send_to_session("test-session", {"type": "clear_cache"})
            assert result is True

            # Client should receive the message
            if conn.poll(timeout=2):
                msg = conn.recv()
                assert msg["type"] == "clear_cache"

            conn.close()
        finally:
            server.stop()


class TestExternalCommand:
    """Tests for external command routing (clear_by_filter)."""

    def test_external_command_routing(self):
        """PipeServer routes clear_by_filter to external command handler."""
        from lineage_tray.pipe_server import PipeServer

        address = _test_pipe_address()
        messages = []
        external_commands = []

        def on_msg(sid, msg):
            messages.append((sid, msg))

        def on_ext_cmd(msg):
            external_commands.append(msg)
            return {"sessions_cleared": 2}

        server = PipeServer(
            on_message=on_msg,
            address=address,
            on_external_command=on_ext_cmd,
        )
        server.start()

        time.sleep(0.3)

        try:
            conn = Client(address, authkey=b"lineage-mcp-tray-v1")
            conn.send({
                "type": "clear_by_filter",
                "base_dir": "C:\\test",
                "client_name": "test-client",
            })

            if conn.poll(timeout=3):
                response = conn.recv()
                assert response["sessions_cleared"] == 2

            conn.close()

            # Should NOT have triggered on_message
            assert len(messages) == 0
            # Should have triggered on_external_command
            assert len(external_commands) == 1
            assert external_commands[0]["type"] == "clear_by_filter"
            assert external_commands[0]["base_dir"] == "C:\\test"
            assert external_commands[0]["client_name"] == "test-client"
        finally:
            server.stop()

    def test_external_command_without_handler(self):
        """PipeServer handles clear_by_filter gracefully when no handler is set."""
        from lineage_tray.pipe_server import PipeServer

        address = _test_pipe_address()
        messages = []

        server = PipeServer(
            on_message=lambda sid, msg: messages.append((sid, msg)),
            address=address,
            # No on_external_command set
        )
        server.start()

        time.sleep(0.3)

        try:
            conn = Client(address, authkey=b"lineage-mcp-tray-v1")
            conn.send({
                "type": "clear_by_filter",
                "base_dir": "C:\\test",
                "client_name": "test-client",
            })

            # Connection should be closed by server (no response expected)
            time.sleep(0.5)
            conn.close()
        finally:
            server.stop()


class TestPrecompactRoundtrip:
    """Integration test for the full precompact hook roundtrip."""

    def test_precompact_roundtrip(self):
        """Test: hook script -> tray -> session clear."""
        address = _test_pipe_address()
        authkey = b"test"
        cleared = []

        def mock_tray():
            """Simulate tray: accept connection, process clear_by_filter."""
            with Listener(address, authkey=authkey) as listener:
                with listener.accept() as conn:
                    msg = conn.recv()
                    assert msg["type"] == "clear_by_filter"
                    assert msg["base_dir"] is not None
                    assert msg["client_name"] == "test-client"
                    conn.send({"sessions_cleared": 1})
                    cleared.append(True)

        t = threading.Thread(target=mock_tray)
        t.start()
        time.sleep(0.2)

        # Simulate what the hook script does
        with Client(address, authkey=authkey) as conn:
            conn.send({
                "type": "clear_by_filter",
                "base_dir": r"C:\git\lineage-mcp",
                "client_name": "test-client",
            })
            if conn.poll(timeout=5.0):
                response = conn.recv()
                assert response["sessions_cleared"] == 1

        t.join(timeout=5)
        assert len(cleared) == 1
