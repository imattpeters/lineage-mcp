"""Test utilities for Lineage MCP tests.

This module provides common test utilities used across all test modules.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


class TempWorkspace:
    """Context manager for creating isolated test workspaces.
    
    Creates a temporary directory and patches path_utils._base_dir
    to point to it, ensuring all path operations are sandboxed.
    
    Usage:
        with TempWorkspace() as ws:
            file_path = ws.create_file("test.txt", "content")
            dir_path = ws.create_dir("subdir")
    """

    def __init__(self) -> None:
        self.tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path = Path()
        self.old_base_dir: Path = Path()

    def __enter__(self) -> "TempWorkspace":
        import path_utils

        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name)
        self.old_base_dir = path_utils._base_dir
        path_utils._base_dir = self.path
        return self

    def __exit__(self, *args: object) -> None:
        import path_utils

        path_utils._base_dir = self.old_base_dir
        if self.tmpdir:
            self.tmpdir.cleanup()

    def create_file(self, relative_path: str, content: str = "") -> Path:
        """Create a file in the workspace.
        
        Args:
            relative_path: Path relative to workspace root
            content: File content to write
            
        Returns:
            Absolute path to created file
        """
        file_path = self.path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def create_dir(self, relative_path: str) -> Path:
        """Create a directory in the workspace.
        
        Args:
            relative_path: Path relative to workspace root
            
        Returns:
            Absolute path to created directory
        """
        dir_path = self.path / relative_path
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path


def run_async(coroutine: object) -> object:
    """Run an async function synchronously for testing.
    
    Handles event loop creation properly to avoid deprecation warnings.
    
    Args:
        coroutine: Coroutine to execute
        
    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)  # type: ignore
