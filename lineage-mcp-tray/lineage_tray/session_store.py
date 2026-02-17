"""In-memory session registry for the tray application.

Stores active lineage-mcp sessions, grouped by base_dir.
"""

import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# Known process names → inferred client name.
# Checked against ancestor_names during registration when client_name
# has not yet been reported by the MCP client.
PROCESS_CLIENT_MAP: dict[str, str] = {
    "code.exe": "Visual Studio Code",
    "code": "Visual Studio Code",
    "opencode.exe": "opencode",
    "opencode": "opencode",
    "claude.exe": "Claude Code",
    "claude": "Claude Code",
}


def infer_client_from_ancestors(ancestor_names: list[str]) -> str | None:
    """Infer client name from ancestor process names.

    Walks the ancestor_names list and returns the first match from
    PROCESS_CLIENT_MAP, or None if no known client is found.

    Args:
        ancestor_names: Process names from get_ancestor_chain().

    Returns:
        Inferred client name, or None.
    """
    for name in ancestor_names:
        lower = name.lower()
        if lower in PROCESS_CLIENT_MAP:
            return PROCESS_CLIENT_MAP[lower]
    return None


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
    ancestor_pids: list[int] = field(default_factory=list)
    ancestor_names: list[str] = field(default_factory=list)

    @property
    def since_str(self) -> str:
        """Human-readable 'since' string."""
        return datetime.fromtimestamp(self.started_at).strftime("%I:%M %p")

    @property
    def ancestor_chain_str(self) -> str:
        """Human-readable ancestor chain for display.

        Returns something like: 'python.exe(1234) → pwsh.exe(5678) → Code.exe(9012)'
        """
        if not self.ancestor_pids:
            return f"PID {self.pid} (no chain)"
        parts = []
        for i, pid in enumerate(self.ancestor_pids):
            name = self.ancestor_names[i] if i < len(self.ancestor_names) else "?"
            parts.append(f"{name}({pid})")
        return " → ".join(parts)

    @property
    def display_name(self) -> str:
        """Short display name for menu."""
        prefix = "⛔ " if self.interrupted else "✅ "
        name = self.client_name or f"PID {self.pid}"
        tool = self.last_tool or self.first_call
        if tool:
            name += f" {tool}"
        return prefix + name


@dataclass
class CompactionEvent:
    """Records a single precompact cache-clear event."""

    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    client_name: Optional[str] = None
    base_dir: str = ""
    ancestor_chain_str: str = ""
    files_tracked: int = 0

    @property
    def time_str(self) -> str:
        """Human-readable timestamp (HH:MM:SS)."""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def display_str(self) -> str:
        """One-line summary for menu display."""
        name = self.client_name or "unknown"
        return f"[{self.time_str}] {name} — {self.files_tracked} files"


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
                session = SessionInfo(**init_data)
                # Infer client name from ancestor processes if not provided
                if not session.client_name and session.ancestor_names:
                    session.client_name = infer_client_from_ancestors(
                        session.ancestor_names
                    )
                self._sessions[session_id] = session

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

    def find_by_filter(
        self,
        base_dir: str | None = None,
        client_name: str | None = None,
        ancestor_pids: list[int] | None = None,
    ) -> list[SessionInfo]:
        """Find sessions matching the given filter criteria.

        Args:
            base_dir: Filter by base directory (normalized path comparison).
                      If None, matches all base_dirs.
            client_name: Filter by client name (case-insensitive substring match).
                         If None, matches all clients.
            ancestor_pids: Filter by ancestor PID chain overlap. If provided,
                           only sessions whose ancestor chains share a common
                           non-system PID with this list will match.

        Returns:
            List of matching SessionInfo objects.
        """
        # System PIDs excluded from ancestor matching
        system_pids = {0, 4}

        with self._lock:
            matches = []
            for session in self._sessions.values():
                if base_dir is not None:
                    # Normalize both paths for comparison
                    session_dir = os.path.normpath(session.base_dir)
                    filter_dir = os.path.normpath(base_dir)
                    if session_dir.lower() != filter_dir.lower():
                        continue

                if ancestor_pids is not None and session.ancestor_pids:
                    # Match by ancestor PID chain overlap
                    hook_set = set(ancestor_pids) - system_pids
                    session_set = set(session.ancestor_pids) - system_pids
                    if not (hook_set & session_set):
                        continue
                elif client_name is not None and session.client_name is not None:
                    # Fallback: match by client name if no ancestor PIDs
                    if client_name.lower() not in session.client_name.lower():
                        continue

                matches.append(session)
            return matches
