"""Session-scoped state management for the MCP file server.

Provides a centralized dataclass for managing all session state,
eliminating scattered global variables.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from config import load_new_session_cooldown_seconds

# Load cooldown at module import
_NEW_SESSION_COOLDOWN_SECONDS: float = load_new_session_cooldown_seconds()


@dataclass
class SessionState:
    """Holds all session-scoped caches that persist until server restart.

    All caches are cleared together on new_session=True or server restart.

    Attributes:
        mtimes: Maps absolute file paths to their last-seen modification times (ms).
        contents: Maps absolute file paths to their last-seen content for diffing.
        provided_folders: Set of folder paths where instruction files have been shown.
        last_new_session_time: Monotonic timestamp of the last new_session clear.
    """

    mtimes: Dict[str, int] = field(default_factory=dict)
    contents: Dict[str, str] = field(default_factory=dict)
    provided_folders: set[str] = field(default_factory=set)
    last_new_session_time: Optional[float] = field(default=None)

    def clear(self) -> None:
        """Clear all session caches unconditionally.

        Called by the explicit clear() tool. Ignores cooldown.
        Also resets the cooldown timer.
        """
        self.mtimes.clear()
        self.contents.clear()
        self.provided_folders.clear()
        self.last_new_session_time = None

    def try_new_session(self) -> bool:
        """Attempt to clear caches for a new_session request.

        If a new_session clear happened within the cooldown window,
        the request is silently ignored to avoid redundant clears
        during the initial burst of tool calls.

        Returns:
            True if caches were actually cleared, False if suppressed by cooldown.
        """
        now = time.monotonic()

        if (
            self.last_new_session_time is not None
            and (now - self.last_new_session_time) < _NEW_SESSION_COOLDOWN_SECONDS
        ):
            return False

        self.mtimes.clear()
        self.contents.clear()
        self.provided_folders.clear()
        self.last_new_session_time = now
        return True

    def track_file(self, file_path: str, mtime_ms: int, content: str) -> None:
        """Track a file's state for change detection.

        Args:
            file_path: Absolute path to the file.
            mtime_ms: Modification time in milliseconds.
            content: Full file content.
        """
        self.mtimes[file_path] = mtime_ms
        self.contents[file_path] = content

    def untrack_file(self, file_path: str) -> None:
        """Remove a file from tracking (e.g., after deletion).

        Args:
            file_path: Absolute path to the file.
        """
        self.mtimes.pop(file_path, None)
        self.contents.pop(file_path, None)

    def mark_folder_provided(self, folder_path: str) -> None:
        """Mark a folder as having its instruction file provided.

        Args:
            folder_path: Absolute path to the folder.
        """
        self.provided_folders.add(folder_path)

    def is_folder_provided(self, folder_path: str) -> bool:
        """Check if a folder's instruction file has been provided.

        Args:
            folder_path: Absolute path to the folder.

        Returns:
            True if already provided, False otherwise.
        """
        return folder_path in self.provided_folders


# Singleton session state instance
session = SessionState()
