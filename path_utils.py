"""Path utilities for the MCP file server.

Provides secure path resolution and validation using pathlib.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass
class PathResult:
    """Result of a path resolution operation.

    Attributes:
        success: Whether the resolution succeeded.
        path: The resolved absolute path (only valid if success=True).
        error: Error message (only set if success=False).
    """

    success: bool
    path: Path
    error: str = ""

    @classmethod
    def ok(cls, path: Path) -> "PathResult":
        """Create a successful result."""
        return cls(success=True, path=path)

    @classmethod
    def err(cls, message: str) -> "PathResult":
        """Create an error result."""
        return cls(success=False, path=Path(), error=message)


# Global base directory - set at startup
_base_dir: Path = Path("/data")


def get_base_dir() -> Path:
    """Get the current base directory.

    Returns:
        The configured base directory as a Path.
    """
    return _base_dir


def set_base_dir(path: Union[str, Path]) -> None:
    """Set the base directory for file operations.

    Args:
        path: The new base directory (will be resolved to absolute).
    """
    global _base_dir
    _base_dir = Path(path).resolve()


def init_base_dir_from_args() -> Path:
    """Initialize base directory from command line arguments.

    Uses first command line argument if provided, otherwise defaults to /data.

    Returns:
        The configured base directory.
    """
    if len(sys.argv) > 1:
        set_base_dir(sys.argv[1])
    return _base_dir


def resolve_path(relative_path: str) -> PathResult:
    """Resolve a relative path to absolute, validating security.

    Ensures the resolved path stays within the base directory to prevent
    directory traversal attacks.

    Args:
        relative_path: Path relative to the base directory.

    Returns:
        PathResult with either the resolved path or an error message.
    """
    try:
        # Resolve to absolute path
        target = (_base_dir / relative_path).resolve()

        # Security check: ensure path is within base directory
        # Use os.path for compatibility with startswith check
        if not str(target).startswith(str(_base_dir)):
            return PathResult.err("Error: Cannot access files outside of the base directory.")

        return PathResult.ok(target)
    except (OSError, ValueError) as e:
        return PathResult.err(f"Error: Invalid path: {e}")


def get_file_mtime_ms(file_path: Path) -> int:
    """Get file modification time in milliseconds.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Modification time in milliseconds as integer.

    Raises:
        OSError: If file cannot be stat'ed.
    """
    return int(file_path.stat().st_mtime * 1000)


def is_instruction_file(file_path: Path, instruction_file_names: list[str]) -> bool:
    """Check if a file is an instruction file.

    Args:
        file_path: Path to the file.
        instruction_file_names: List of valid instruction file names.

    Returns:
        True if the file name matches an instruction file name.
    """
    return file_path.name in instruction_file_names
