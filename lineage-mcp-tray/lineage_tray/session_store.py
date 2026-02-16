"""In-memory session registry for the tray application.

Stores active lineage-mcp sessions, grouped by base_dir.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SessionInfo:
    """Represents one active lineage-mcp session."""

    session_id: str
    pid: int
    base_dir: str
    started_at: float  # time.time() epoch
    client_name: Optional[str] = None  # e.g. "vscode-copilot", "claude-desktop"
    first_call: Optional[str] = None  # e.g. "[edit:C:/a_file.md]"
    last_tool: Optional[str] = None  # e.g. "[read:src/main.py]" — most recent tool
    files_tracked: int = 0
    last_seen: float = field(default_factory=time.time)
    interrupted: bool = False

    @property
    def since_str(self) -> str:
        """Human-readable 'since' string."""
        return datetime.fromtimestamp(self.started_at).strftime("%I:%M %p")

    @property
    def display_name(self) -> str:
        """Short display name for menu."""
        prefix = "⛔ " if self.interrupted else "✅ "
        name = self.client_name or f"PID {self.pid}"
        tool = self.last_tool or self.first_call
        if tool:
            name += f" {tool}"
        return prefix + name


class SessionStore:
    """Thread-safe in-memory registry of active sessions, grouped by base_dir."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionInfo] = {}  # session_id → SessionInfo
        self._lock = threading.Lock()

    def register(self, data: dict) -> None:
        """Register or update a session.

        Args:
            data: Dict with session fields. Must include 'session_id'.
        """
        with self._lock:
            session_id = data["session_id"]
            if session_id in self._sessions:
                # Update existing
                for k, v in data.items():
                    if k != "type" and v is not None:
                        setattr(self._sessions[session_id], k, v)
                self._sessions[session_id].last_seen = time.time()
            else:
                # New registration — filter out 'type' key
                init_data = {k: v for k, v in data.items() if k != "type"}
                self._sessions[session_id] = SessionInfo(**init_data)

    def unregister(self, session_id: str) -> None:
        """Remove a session.

        Args:
            session_id: The session to remove.
        """
        with self._lock:
            self._sessions.pop(session_id, None)

    def update(self, session_id: str, data: dict) -> None:
        """Update fields of an existing session.

        Args:
            session_id: The session to update.
            data: Dict of fields to update.
        """
        with self._lock:
            if session_id in self._sessions:
                for k, v in data.items():
                    if k not in ("type", "session_id") and v is not None:
                        setattr(self._sessions[session_id], k, v)
                self._sessions[session_id].last_seen = time.time()

    def get_grouped(self) -> dict[str, list[SessionInfo]]:
        """Return sessions grouped by base_dir, sorted by started_at.

        Returns:
            Dict mapping base_dir strings to lists of SessionInfo.
        """
        with self._lock:
            groups: dict[str, list[SessionInfo]] = defaultdict(list)
            for s in self._sessions.values():
                groups[s.base_dir].append(s)
            # Sort each group by started_at
            for key in groups:
                groups[key].sort(key=lambda s: s.started_at)
            return dict(groups)

    def get(self, session_id: str) -> SessionInfo | None:
        """Get a specific session.

        Args:
            session_id: The session to look up.

        Returns:
            SessionInfo if found, None otherwise.
        """
        with self._lock:
            return self._sessions.get(session_id)

    @property
    def count(self) -> int:
        """Number of active sessions."""
        with self._lock:
            return len(self._sessions)
