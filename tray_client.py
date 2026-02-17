"""Named pipe client for registering with the lineage-mcp-tray process.

This module is part of the lineage-mcp server. It connects to the tray
application (if running) and sends session registration and update messages.

All operations are fire-and-forget — the tray is optional and failures
are silently ignored to avoid impacting the core MCP server.
"""

import atexit
import os
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Client
from pathlib import Path

from hooks.pid_utils import get_ancestor_chain


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


PIPE_ADDRESS = get_pipe_address()
PIPE_AUTHKEY = b"lineage-mcp-tray-v1"


class TrayClient:
    """Connects to the tray process and sends session updates.

    All public methods are designed to never raise exceptions — failures
    are logged internally and the client silently becomes a no-op.

    Args:
        base_dir: The base directory this lineage-mcp instance serves.
    """

    def __init__(self, base_dir: str) -> None:
        self.session_id = f"{os.getpid()}_{int(time.time())}"
        self.base_dir = base_dir
        self.conn = None
        self._connected = False
        self._lock = threading.Lock()
        self._listener_thread: threading.Thread | None = None
        self._last_reconnect_attempt: float = 0.0
        self._reconnect_interval: float = 10.0  # seconds between reconnect attempts
        self._connection_generation: int = 0  # bumps on each reconnect

    def connect(self) -> bool:
        """Try to connect to the tray pipe.

        Non-blocking. Returns False if tray is not running.
        Never raises exceptions.

        Returns:
            True if connected successfully, False otherwise.
        """
        try:
            self.conn = Client(PIPE_ADDRESS, authkey=PIPE_AUTHKEY)
            self._connected = True

            # Send registration
            ancestor_chain = get_ancestor_chain()
            self.conn.send(
                {
                    "type": "register",
                    "session_id": self.session_id,
                    "pid": os.getpid(),
                    "base_dir": self.base_dir,
                    "started_at": time.time(),
                    "client_name": None,  # Updated later from clientInfo
                    "first_call": None,  # Updated on first tool call
                    "files_tracked": 0,
                    "ancestor_pids": [pid for pid, _ in ancestor_chain],
                    "ancestor_names": [name for _, name in ancestor_chain],
                }
            )

            # Start listening for commands from tray
            self._listener_thread = threading.Thread(
                target=self._listen_for_commands, daemon=True
            )
            self._listener_thread.start()

            return True
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            self._connected = False
            return False
        except Exception:
            self._connected = False
            return False

    def _try_reconnect(self) -> bool:
        """Attempt to reconnect if disconnected (rate-limited).

        Called opportunistically from update methods. At most one attempt
        every ``_reconnect_interval`` seconds to avoid flooding.
        On successful reconnect, bumps connection generation so callers
        know to re-send session info.

        Returns:
            True if now connected, False otherwise.
        """
        if self._connected:
            return True

        now = time.monotonic()
        if now - self._last_reconnect_attempt < self._reconnect_interval:
            return False
        self._last_reconnect_attempt = now

        # Close old connection if any
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

        # Wait for old listener thread to fully stop before reconnecting
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
        self._listener_thread = None

        result = self.connect()
        if result:
            self._connection_generation += 1
        return result

    def _listen_for_commands(self) -> None:
        """Listen for commands from tray (clear cache, interrupt, etc.)."""
        # Capture the connection object for this listener session so we only
        # loop while OUR connection is still the active one.
        my_conn = self.conn
        while self._connected and self.conn is my_conn:
            try:
                if my_conn and my_conn.poll(timeout=1.0):
                    msg = my_conn.recv()
                    self._handle_command(msg)
            except (EOFError, OSError):
                # Only set _connected=False if we're still the active connection
                if self.conn is my_conn:
                    self._connected = False
                break
            except Exception:
                if self.conn is my_conn:
                    self._connected = False
                break

    def _handle_command(self, msg: dict) -> None:
        """Handle a command from the tray process.

        Args:
            msg: The command message dict.
        """
        cmd = msg.get("type")
        if cmd == "clear_cache":
            from session_state import session

            session.try_new_session()
        elif cmd == "interrupt":
            from session_state import session

            session.interrupted = True
        elif cmd == "resume":
            from session_state import session

            session.resume()

    def update(self, **kwargs: object) -> None:
        """Send an update to the tray.

        Fire-and-forget. If disconnected, attempts to reconnect first.

        Args:
            **kwargs: Fields to update (e.g., client_name, files_tracked).
        """
        if not self._connected:
            self._try_reconnect()
        if not self._connected:
            return
        try:
            self.conn.send(
                {"type": "update", "session_id": self.session_id, **kwargs}
            )
        except (OSError, BrokenPipeError):
            self._connected = False
        except Exception:
            self._connected = False

    def disconnect(self) -> None:
        """Clean disconnect from tray. Safe to call multiple times."""
        was_connected = self._connected
        self._connected = False

        if self.conn:
            try:
                if was_connected:
                    self.conn.send(
                        {
                            "type": "unregister",
                            "session_id": self.session_id,
                        }
                    )
            except (OSError, BrokenPipeError):
                pass
            except Exception:
                pass
            finally:
                try:
                    self.conn.close()
                except (OSError, BrokenPipeError):
                    pass
                except Exception:
                    pass
                self.conn = None


def ensure_tray_running() -> bool:
    """Attempt to start the tray process if not already running.

    Returns True if tray is (now) running, False otherwise.
    Never raises exceptions.
    """
    # First, try to connect to the pipe
    try:
        conn = Client(PIPE_ADDRESS, authkey=PIPE_AUTHKEY)
        conn.close()
        return True  # Tray already running
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        pass  # Tray not running — try to start it

    # Try to launch tray
    try:
        # Use pythonw.exe on Windows to avoid console window
        python = sys.executable
        if sys.platform == "win32":
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if Path(pythonw).exists():
                python = pythonw

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = (
                getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

        subprocess.Popen(
            [python, "-m", "lineage_tray"],
            creationflags=creation_flags,
            close_fds=True,
        )

        # Wait briefly for tray to start
        for _ in range(10):  # Try for 2 seconds
            time.sleep(0.2)
            try:
                conn = Client(PIPE_ADDRESS, authkey=PIPE_AUTHKEY)
                conn.close()
                return True
            except (ConnectionRefusedError, FileNotFoundError, OSError):
                continue

        return False
    except (FileNotFoundError, OSError):
        return False  # lineage-tray not installed
    except Exception:
        return False


# Module-level tray client instance (initialized by lineage.py)
_tray_client: TrayClient | None = None
_first_call_sent = False
_client_name_sent = False
_known_generation: int = 0


def init_tray_client(base_dir: str) -> TrayClient | None:
    """Initialize and connect the tray client.

    Attempts to start the tray if not running, then connects.
    Always keeps the TrayClient instance so reconnection can happen
    later if the tray starts or restarts.

    Args:
        base_dir: The base directory this lineage-mcp serves.

    Returns:
        The TrayClient instance, or None if connection failed.
    """
    global _tray_client

    # Try to ensure tray is running (auto-launch)
    ensure_tray_running()

    _tray_client = TrayClient(base_dir)
    if _tray_client.connect():
        atexit.register(_tray_client.disconnect)
        return _tray_client
    else:
        # Keep _tray_client alive — reconnect will be attempted on tool calls
        atexit.register(_tray_client.disconnect)
        return None


def update_tray_first_call(
    tool_name: str, args_summary: str, client_name: str | None = None
) -> None:
    """Update tray with client info on first tool call.

    Sends first_call info once, and keeps retrying client_name until
    it's successfully sent (may not be available on the very first call).
    Resets flags on reconnect so the new tray gets current info.

    Args:
        tool_name: Name of the first tool called.
        args_summary: Summary of the tool arguments.
        client_name: MCP client name if available.
    """
    global _first_call_sent, _client_name_sent, _known_generation
    if _tray_client is None:
        return

    # If disconnected, try reconnect (which also re-registers)
    if not _tray_client._connected:
        _tray_client._try_reconnect()
    if not _tray_client._connected:
        return

    # Reset flags if generation changed (reconnection happened)
    if _tray_client._connection_generation != _known_generation:
        _known_generation = _tray_client._connection_generation
        _first_call_sent = False
        _client_name_sent = False

    # Nothing left to send
    if _first_call_sent and _client_name_sent:
        return

    update_kwargs: dict[str, object] = {}

    if not _first_call_sent:
        _first_call_sent = True
        update_kwargs["first_call"] = f"[{tool_name}:{args_summary}]"

    if not _client_name_sent and client_name:
        _client_name_sent = True
        update_kwargs["client_name"] = client_name

    if update_kwargs:
        _tray_client.update(**update_kwargs)


def update_tray_files_tracked(
    count: int, tool_name: str = "", args_summary: str = ""
) -> None:
    """Update the tray with the current files tracked count and last tool.

    Args:
        count: Number of files currently tracked.
        tool_name: Name of the tool being called.
        args_summary: Brief summary of tool arguments.
    """
    if _tray_client is None:
        return
    if not _tray_client._connected:
        _tray_client._try_reconnect()
    if not _tray_client._connected:
        return
    update_kwargs: dict[str, object] = {"files_tracked": count}
    if tool_name:
        update_kwargs["last_tool"] = f"[{tool_name}:{args_summary}]"
    _tray_client.update(**update_kwargs)
