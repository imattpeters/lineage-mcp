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
    new_session_clear_count: int = field(default=0)
    interrupted: bool = field(default=False)

    def clear(self) -> None:
        """Clear all session caches unconditionally.

        Called by the explicit clear() tool. Ignores cooldown.
        Also resets the cooldown timer.
        Increments clear count (never reset) so base instruction files
        are included after the first compaction.
        """
        self.mtimes.clear()
        self.contents.clear()
        self.provided_folders.clear()
        self.last_new_session_time = None
        self.new_session_clear_count += 1

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
        self.new_session_clear_count += 1
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

    def should_include_base_instruction_files(self) -> bool:
        """Check if base directory instruction files should be included.

        On the first session, the harness (VS Code, OpenCode) loads the base
        AGENTS.md/CLAUDE.md. After context compaction triggers a second
        new_session clear, the LLM has lost that context and needs the base
        instruction files re-provided.

        Returns:
            True if clear count >= 2 (i.e., at least one compaction has occurred).
        """
        return self.new_session_clear_count >= 2

    def check_interrupted(self) -> bool:
        """Check if the session is in interrupted mode.

        When interrupted, ALL tool calls should return only the interrupt
        message. The interrupted state persists until resume() is called
        (via the system tray Resume action).

        Returns:
            True if the session is interrupted, False otherwise.
        """
        return self.interrupted

    def resume(self) -> None:
        """Clear the interrupted flag, returning to normal operation.

        Called when the user clicks Resume in the system tray.
        """
        self.interrupted = False


# Singleton session state instance
session = SessionState()
