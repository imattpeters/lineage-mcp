"""Named pipe server that accepts connections from lineage-mcp instances.

Uses multiprocessing.connection for cross-platform named pipe / socket IPC.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from multiprocessing.connection import Listener, wait
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from lineage_tray.message_log import MessageLog

logger = logging.getLogger("lineage_tray.pipe_server")


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
        on_external_command: Callable[[dict], dict] | None = None,
    ) -> None:
        self.on_message = on_message
        self.on_external_command = on_external_command
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
        logger.info("Starting pipe server on %s", self.address)

        # On Unix, clean up stale socket file before binding
        if sys.platform != "win32" and os.path.exists(self.address):
            try:
                os.unlink(self.address)
                logger.debug("Removed stale socket file: %s", self.address)
            except OSError:
                logger.warning("Could not remove stale socket: %s", self.address)

        self.listener = Listener(self.address, authkey=self.authkey)

        # Thread 1: Accept new connections
        threading.Thread(
            target=self._accept_loop, daemon=True, name="pipe-accept"
        ).start()

        # Thread 2: Read messages from existing connections
        threading.Thread(
            target=self._read_loop, daemon=True, name="pipe-read"
        ).start()

        logger.info("Pipe server started")

    def _accept_loop(self) -> None:
        """Accept new incoming connections."""
        while self._running:
            conn = None
            try:
                conn = self.listener.accept()
                try:
                    msg = conn.recv()
                    msg_type = msg.get("type")

                    if msg_type == "register":
                        # Existing behavior: lineage-mcp session registration
                        session_id = msg["session_id"]
                        logger.debug(
                            "Accepted connection for session %s (pid=%s)",
                            session_id,
                            msg.get("pid"),
                        )
                        with self._lock:
                            self.connections[session_id] = conn
                        if self.message_log:
                            self.message_log.log_received(session_id, msg)
                        self.on_message(session_id, msg)

                    elif msg_type == "clear_by_filter":
                        # External command: hook script requesting cache clear
                        logger.debug("External command: clear_by_filter")
                        self._handle_external_command(conn, msg)

                    else:
                        # Invalid first message - close connection
                        logger.warning(
                            "Rejected connection: unexpected first message type %r",
                            msg_type,
                        )
                        conn.close()
                        conn = None
                except (EOFError, OSError) as exc:
                    logger.debug("Connection error during handshake: %s", exc)
                    if conn:
                        try:
                            conn.close()
                        except OSError:
                            pass
                        conn = None
            except OSError as exc:
                if conn:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    conn = None
                if self._running:
                    logger.warning("Accept error (retrying): %s", exc)
                    time.sleep(0.5)  # Brief pause before retrying
                    continue
                break
            except Exception as exc:
                # Catch-all: log and retry rather than crashing the thread
                if conn:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    conn = None
                if self._running:
                    logger.error(
                        "Unexpected error in accept loop (retrying): %s",
                        exc,
                        exc_info=True,
                    )
                    time.sleep(1.0)
                    continue
                break

    def _handle_external_command(self, conn, msg) -> None:
        """Handle a command from an external script (not a registered session).

        The connection is short-lived: send response and close.
        """
        try:
            cmd = msg.get("type")
            if self.message_log:
                # Log the incoming external command with a synthetic session ID
                ext_label = f"hook:{msg.get('client_name', 'unknown')}"
                self.message_log.log_received(ext_label, msg)
            if cmd == "clear_by_filter" and self.on_external_command:
                result = self.on_external_command(msg)
                conn.send(result)
                if self.message_log:
                    self.message_log.log_sent(ext_label, result)
        except (OSError, BrokenPipeError) as exc:
            logger.warning("Error handling external command: %s", exc)
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _read_loop(self) -> None:
        """Poll all connections for incoming messages."""
        while self._running:
            try:
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
                except (OSError, ValueError) as exc:
                    # Connection was closed by another thread or became invalid
                    logger.debug("wait() error in read loop: %s", exc)
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
                        # Connection closed - session ended
                        logger.debug(
                            "Connection lost for session %s (disconnected)", session_id
                        )
                        with self._lock:
                            closed_conn = self.connections.pop(session_id, None)
                            if closed_conn and closed_conn is not conn:
                                # We removed a different connection - put it back
                                self.connections[session_id] = closed_conn
                        self.on_message(session_id, {"type": "unregister"})
            except Exception as exc:
                # Catch-all: log and continue rather than crashing the thread
                if self._running:
                    logger.error(
                        "Unexpected error in read loop (continuing): %s",
                        exc,
                        exc_info=True,
                    )
                    time.sleep(0.5)

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
            logger.warning(
                "Cannot send to session %s: not connected", session_id
            )
            return False
        try:
            conn.send(message)
            logger.debug(
                "Sent %s to session %s", message.get("type", "?"), session_id
            )
            if self.message_log:
                self.message_log.log_sent(session_id, message)
            return True
        except (OSError, BrokenPipeError) as exc:
            logger.warning(
                "Send failed for session %s (%s): %s",
                session_id,
                message.get("type", "?"),
                exc,
            )
            with self._lock:
                self.connections.pop(session_id, None)
            return False

    def stop(self) -> None:
        """Shut down the pipe server and close all connections."""
        logger.info("Stopping pipe server")
        self._running = False
        with self._lock:
            for sid, conn in self.connections.items():
                try:
                    conn.close()
                    logger.debug("Closed connection for session %s", sid)
                except OSError:
                    pass
            self.connections.clear()
        if self.listener:
            try:
                self.listener.close()
            except OSError:
                pass
        logger.info("Pipe server stopped")
