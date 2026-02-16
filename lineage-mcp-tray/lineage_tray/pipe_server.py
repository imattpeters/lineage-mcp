"""Named pipe server that accepts connections from lineage-mcp instances.

Uses multiprocessing.connection for cross-platform named pipe / socket IPC.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from multiprocessing.connection import Listener, wait
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from lineage_tray.message_log import MessageLog


def get_pipe_address() -> str:
    """Get the platform-appropriate pipe address.

    Returns:
        Named pipe path (Windows) or Unix socket path (macOS/Linux).
    """
    if sys.platform == "win32":
        return r"\\.\pipe\lineage-mcp-tray"
    else:
        import tempfile

        return os.path.join(tempfile.gettempdir(), "lineage-mcp-tray.sock")


# Default pipe address and auth key
PIPE_ADDRESS = get_pipe_address()
PIPE_AUTHKEY = b"lineage-mcp-tray-v1"


class PipeServer:
    """Named pipe server that accepts connections from lineage-mcp instances.

    Args:
        on_message: Callback invoked with (session_id, message_dict) for each
                    incoming message. Called from background threads.
        address: Pipe address to listen on. Defaults to platform-appropriate value.
        authkey: Authentication key for pipe connections.
    """

    def __init__(
        self,
        on_message: Callable[[str, dict], None],
        address: str | None = None,
        authkey: bytes = PIPE_AUTHKEY,
        message_log: MessageLog | None = None,
    ) -> None:
        self.on_message = on_message
        self.address = address or PIPE_ADDRESS
        self.authkey = authkey
        self.message_log = message_log
        self.connections: dict[str, object] = {}  # {session_id: Connection}
        self.listener: Listener | None = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the pipe server in background threads.

        Creates two daemon threads:
        - Accept thread: listens for new connections
        - Read thread: polls existing connections for messages
        """
        self._running = True
        self.listener = Listener(self.address, authkey=self.authkey)

        # Thread 1: Accept new connections
        threading.Thread(target=self._accept_loop, daemon=True).start()

        # Thread 2: Read messages from existing connections
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _accept_loop(self) -> None:
        """Accept new incoming connections."""
        while self._running:
            conn = None
            try:
                conn = self.listener.accept()
                # First message must be a registration with session_id
                try:
                    msg = conn.recv()
                    if msg.get("type") == "register":
                        session_id = msg["session_id"]
                        with self._lock:
                            self.connections[session_id] = conn
                        if self.message_log:
                            self.message_log.log_received(session_id, msg)
                        self.on_message(session_id, msg)
                    else:
                        # Invalid first message - close connection
                        conn.close()
                        conn = None
                except (EOFError, OSError):
                    if conn:
                        conn.close()
                        conn = None
            except OSError:
                if conn:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    conn = None
                if self._running:
                    continue
                break

    def _read_loop(self) -> None:
        """Poll all connections for incoming messages."""
        while self._running:
            with self._lock:
                # Make a copy of connections to avoid modification during iteration
                conns = list(self.connections.items())

            if not conns:
                time.sleep(0.5)
                continue

            # Wait for any connection to have data (timeout 1s)
            conn_list = [c for _, c in conns]
            ready = []
            try:
                ready = wait(conn_list, timeout=1.0)
            except (OSError, ValueError):
                # Connection was closed by another thread or became invalid
                time.sleep(0.1)
                continue

            for conn in ready:
                # Find session_id for this connection
                session_id = None
                for sid, c in conns:
                    if c is conn:
                        session_id = sid
                        break

                if session_id is None:
                    continue

                try:
                    msg = conn.recv()
                    if self.message_log:
                        self.message_log.log_received(session_id, msg)
                    self.on_message(session_id, msg)
                except (EOFError, OSError):
                    # Connection closed — session ended
                    with self._lock:
                        closed_conn = self.connections.pop(session_id, None)
                        if closed_conn and closed_conn is not conn:
                            # We removed a different connection - put it back
                            self.connections[session_id] = closed_conn
                    self.on_message(session_id, {"type": "unregister"})

    def send_to_session(self, session_id: str, message: dict) -> bool:
        """Send a message back to a specific lineage-mcp session.

        Args:
            session_id: Target session identifier.
            message: Dict to send (serialized via pickle by multiprocessing).

        Returns:
            True if sent successfully, False if session not found or send failed.
        """
        with self._lock:
            conn = self.connections.get(session_id)
        if conn is None:
            return False
        try:
            conn.send(message)
            if self.message_log:
                self.message_log.log_sent(session_id, message)
            return True
        except (OSError, BrokenPipeError):
            with self._lock:
                self.connections.pop(session_id, None)
            return False

    def stop(self) -> None:
        """Shut down the pipe server and close all connections."""
        self._running = False
        with self._lock:
            for conn in self.connections.values():
                try:
                    conn.close()
                except OSError:
                    pass
            self.connections.clear()
        if self.listener:
            try:
                self.listener.close()
            except OSError:
                pass
