"""Thread-safe message log for pipe communication.

Records all messages sent to and received from MCP server sessions.
Uses a circular buffer to keep memory bounded.
"""

from __future__ import annotations

import copy
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LogEntry:
    """A single logged message."""

    timestamp: float = field(default_factory=time.time)
    direction: str = "received"  # "received" (← from server) or "sent" (→ to server)
    session_id: str = ""
    message: dict[str, Any] = field(default_factory=dict)

    @property
    def time_str(self) -> str:
        """Human-readable timestamp (HH:MM:SS)."""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def direction_arrow(self) -> str:
        """Arrow indicating direction."""
        return "←" if self.direction == "received" else "→"

    def format(self, session_label: str | None = None) -> str:
        """Format the log entry for display.

        Args:
            session_label: Optional human-readable session label.

        Returns:
            Formatted string like "[12:34:05] ← s1: {type: register, ...}"
        """
        label = session_label or self.session_id
        # Compact message representation
        msg_type = self.message.get("type", "?")
        extras = {k: v for k, v in self.message.items() if k not in ("type", "session_id")}
        if extras:
            extras_str = ", ".join(f"{k}={_compact(v)}" for k, v in extras.items())
            msg_repr = f"{msg_type} ({extras_str})"
        else:
            msg_repr = msg_type
        return f"[{self.time_str}] {self.direction_arrow} {label}: {msg_repr}"


def _compact(value: Any, max_len: int = 40) -> str:
    """Compact representation of a value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


class MessageLog:
    """Thread-safe circular buffer for pipe messages.

    Args:
        max_entries: Maximum number of entries to keep. Oldest entries
            are dropped when the buffer is full.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def log_received(self, session_id: str, message: dict[str, Any]) -> None:
        """Log a message received from an MCP server session.

        Args:
            session_id: The session that sent the message.
            message: The message dict.
        """
        entry = LogEntry(
            direction="received",
            session_id=session_id,
            message=copy.deepcopy(message),  # Deep copy to avoid mutation
        )
        with self._lock:
            self._entries.append(entry)

    def log_sent(self, session_id: str, message: dict[str, Any]) -> None:
        """Log a message sent to an MCP server session.

        Args:
            session_id: The target session.
            message: The message dict.
        """
        entry = LogEntry(
            direction="sent",
            session_id=session_id,
            message=copy.deepcopy(message),
        )
        with self._lock:
            self._entries.append(entry)

    def get_recent(self, n: int = 10) -> list[LogEntry]:
        """Get the most recent log entries.

        Args:
            n: Number of recent entries to return.

        Returns:
            List of LogEntry objects, oldest first.
        """
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    @property
    def count(self) -> int:
        """Total number of entries currently stored."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Clear all log entries."""
        with self._lock:
            self._entries.clear()
