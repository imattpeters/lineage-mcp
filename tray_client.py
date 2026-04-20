"""Named pipe client for registering with the lineage-mcp-tray process.

This module is part of the lineage-mcp server. It connects to the tray
application (if running) and sends session registration and update messages.

All operations are fire-and-forget - the tray is optional and failures
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


def _format_tool_arg(key: str, value: object, max_preview_len: int = 20) -> str:
    """Format a single tool argument for logging.

    Control parameters (flags, counts, limits) are shown in full.
    Data parameters (strings, paths) show first N characters + length.

    Args:
        key: Parameter name
        value: Parameter value
        max_preview_len: Max characters to show for string/data params

    Returns:
        Formatted string like 'key=value' or 'key="preview..." (len chars)'
    """
    # Skip None values
    if value is None:
        return f"{key}=None"

    # Control parameters - show in full
    if key in ("show_line_numbers", "cursor", "offset", "limit",
               "timeout", "max_results", "maxlen", "on_error"):
        return f"{key}={value}"

    # Booleans - show in full
    if isinstance(value, bool):
        return f"{key}={value}"

    # Numbers - show in full
    if isinstance(value, (int, float)):
        return f"{key}={value}"

    # Lists/arrays - show type and count
    if isinstance(value, (list, dict)):
        return f"{key}(type={type(value).__name__}, len={len(value)})"

    # Strings - preview first N chars
    s = str(value)
    if len(s) > max_preview_len:
        char_count = len(s)
        preview = s[:max_preview_len]
        return f'{key}="{preview}..." ({char_count} chars)'
    else:
        return f'{key}="{s}"'


def format_tool_call(tool_name: str, **kwargs) -> str:
    """Format a tool call with parameters for logging.

    Args:
        tool_name: Name of the tool
        **kwargs: Tool parameters

    Returns:
        Formatted string like 'read: src/app.py, offset=100, limit=50'
    """
    # Extract file_path or pattern as the primary identifier
    file_path = kwargs.pop("file_path", None) or kwargs.pop("pattern", None)

    formatted_args = []
    if file_path:
        formatted_args.append(str(file_path))

    # Format remaining args
    for key, value in kwargs.items():
        if key not in ("ctx",):  # Skip context
            formatted_args.append(_format_tool_arg(key, value))

    args_str = ", ".join(formatted_args)
    return f"{tool_name}: {args_str}" if args_str else tool_name


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

    All public methods are designed to never raise exceptions - failures
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

            # Get current interrupt state so tray picks it up on (re)connect
            interrupted = False
            try:
                from session_state import session
                interrupted = session.interrupted
            except Exception:
                pass

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
                    "interrupted": interrupted,
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

    def send_message(self, msg: dict) -> None:
        """Send an arbitrary message to the tray.

        Fire-and-forget. If disconnected, attempts to reconnect first.

        Args:
            msg: Message dict to send.
        """
        if not self._connected:
            self._try_reconnect()
        if not self._connected:
            return
        try:
            self.conn.send({**msg, "session_id": self.session_id})
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
        pass  # Tray not running - try to start it

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


def _extract_client_name(ctx: object | None) -> str | None:
    """Extract the MCP client name from a Context object.

    Duck-typed to avoid importing mcp types into this module.

    Args:
        ctx: MCP Context object (or None).

    Returns:
        Client name string, or None.
    """
    try:
        if ctx and ctx.session and ctx.session.client_params:
            return ctx.session.client_params.clientInfo.name
    except (AttributeError, TypeError):
        pass
    return None


def log_tool_call(tool_name: str, *, ctx: object | None = None, **kwargs) -> None:
    """Log a tool call with full parameters to the tray.

    Also sends the client name (once per session) if ctx is provided.

    Args:
        tool_name: Name of the tool (e.g. 'read', 'modify', 'delete')
        ctx: Optional MCP Context for client name extraction.
        **kwargs: Tool arguments (file_path, pattern, content, offset, limit, etc.)
    """
    if _tray_client is None:
        return

    if not _tray_client._connected:
        _tray_client._try_reconnect()
    if not _tray_client._connected:
        return

    try:
        # Send client name update (once per session)
        if ctx is not None:
            client_name = _extract_client_name(ctx)
            update_tray_client_name(client_name)

        formatted_call = format_tool_call(tool_name, **kwargs)
        _tray_client.send_message({
            "type": "tool_call",
            "tool": tool_name,
            "summary": formatted_call,
        })
    except Exception:
        pass  # Tray logging is best-effort


def update_tray_client_name(client_name: str | None) -> None:
    """Update tray with client name (once per session).

    Args:
        client_name: MCP client name.
    """
    if _tray_client is None:
        return

    # If disconnected, try reconnect (which also re-registers)
    if not _tray_client._connected:
        _tray_client._try_reconnect()
    if not _tray_client._connected:
        return

    # Reset flags if generation changed (reconnection happened)
    global _first_call_sent, _client_name_sent, _known_generation
    if _tray_client._connection_generation != _known_generation:
        _known_generation = _tray_client._connection_generation
        _first_call_sent = False
        _client_name_sent = False

    if not _client_name_sent and client_name:
        _client_name_sent = True
        try:
            _tray_client.update(client_name=client_name)
        except Exception:
            pass  # Tray updates are best-effort


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
        # Keep _tray_client alive - reconnect will be attempted on tool calls
        atexit.register(_tray_client.disconnect)
        return None



