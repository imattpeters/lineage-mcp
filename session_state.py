"""Session-scoped state management for the MCP file server.

Provides a centralized dataclass for managing all session state,
eliminating scattered global variables.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SessionState:
    """Holds all session-scoped caches that persist until server restart.

    All caches are cleared together on new_session=True or server restart.

    Attributes:
        mtimes: Maps absolute file paths to their last-seen modification times (ms).
        contents: Maps absolute file paths to their last-seen content for diffing.
        provided_folders: Set of folder paths where instruction files have been shown.
    """

    mtimes: Dict[str, int] = field(default_factory=dict)
    contents: Dict[str, str] = field(default_factory=dict)
    provided_folders: set[str] = field(default_factory=set)

    def clear(self) -> None:
        """Clear all session caches.

        Called on new_session=True or when resetting state.
        """
        self.mtimes.clear()
        self.contents.clear()
        self.provided_folders.clear()

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
