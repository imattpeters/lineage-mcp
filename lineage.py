"""Lineage MCP - Entry point and tool registration.

A Model Context Protocol server for file operations with change detection
and instruction file discovery.
"""

import sys
from typing import Dict, List

from mcp.server.fastmcp import FastMCP

from config import ENABLE_MULTI_EDIT, ENABLE_MULTI_READ
from path_utils import init_base_dir_from_args
from tools import (
    clear_cache,
    delete_file,
    edit_file,
    list_files,
    multi_edit_file,
    multi_read_file,
    read_file,
    search_files,
    write_file,
)

# Initialize base directory from command line argument
init_base_dir_from_args()

# Create MCP server instance
mcp = FastMCP("lineage")


# Register tools with MCP server
@mcp.tool()
async def list(path: str = "", new_session: bool = False) -> str:
    """List all files in the specified directory.

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        path: Optional subdirectory path relative to the base directory
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.

    Returns:
        Markdown formatted table of files/directories with metadata and changed files section.
    """
    return await list_files(path, new_session)


@mcp.tool()
async def search(pattern: str, path: str = "", new_session: bool = False) -> str:
    """Search for files matching a glob pattern.

    Searches for files using glob patterns (e.g., "*.txt", "**/*.py", "src/*/config.json").
    Supports recursive patterns with ** syntax. Returns list of matching file paths
    relative to the base directory.

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        pattern: Glob pattern to search for (e.g., "*.txt", "src/**/*.py")
        path: Optional subdirectory to search within (relative to base directory)
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.

    Returns:
        List of matching file paths, or error message if pattern is invalid.
    """
    return await search_files(pattern, path, new_session)


@mcp.tool()
async def read(
    file_path: str,
    new_session: bool = False,
    show_line_numbers: bool = False,
    offset: int | None = None,
    limit: int | None = None,
    page: int | None = None,
) -> str:
    """Read the contents of a file.

    Tracks file modification time for change detection [on subsequent reads you
    will be notified of file changes to file you've read] and discovers AGENTS.md
    files from parent directories and appends them to the read.

    Supports two pagination methods:
    1. Line-based: Use offset and limit for specific line ranges
    2. Character-based: Use page for automatic pagination (configurable limit)

    When a file exceeds the character limit (default 50,000), it is automatically
    paginated with line-aware truncation. Each page shows complete lines only.

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        file_path: Path to the file relative to the base directory
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.
        show_line_numbers: If True, format output with line numbers (N→content). Defaults to False.
        offset: Optional 0-based line number to start reading from. If None, starts at line 0.
                If offset >= total lines, returns empty result.
                Cannot be used with 'page' parameter.
        limit: Optional number of lines to read. If None, reads to end of file.
               If limit=0 or offset beyond EOF, returns empty result.
               Cannot be used with 'page' parameter.
        page: Optional page number for character-based pagination (0-indexed).
              Automatically paginates files exceeding the character limit.
              Each page contains complete lines only (line-aware truncation).
              Use continuation messages to navigate to next pages.
              Cannot be used with 'offset' or 'limit' parameters.

    Returns:
        File contents (full or partial) with optional line numbers.
        For paginated reads: includes page indicator, character count,
        line range, and continuation instructions.
        [CHANGED_FILES] and [AGENTS.MD] sections appended as usual.
    """
    return await read_file(
        file_path, new_session, show_line_numbers, offset, limit, page
    )


@mcp.tool()
async def write(file_path: str, content: str, new_session: bool = False) -> str:
    """Write content to a file.

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        file_path: Path to the file relative to the base directory
        content: Content to write to the file
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.

    Returns:
        Success or error message
    """
    return await write_file(file_path, content, new_session)


@mcp.tool()
async def edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    new_session: bool = False,
) -> str:
    """Edit a file by replacing exact string matches.

    Performs targeted string replacements in a file. The old_string must exist
    in the file and be unique (unless replace_all is True).

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        file_path: Path to the file relative to the base directory
        old_string: Exact text to find and replace (must match exactly including whitespace)
        new_string: Text to replace old_string with
        replace_all: If True, replace all occurrences; if False, old_string must be unique
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.

    Returns:
        Success message with replacement count, or error message
    """
    return await edit_file(file_path, old_string, new_string, replace_all, new_session)


if ENABLE_MULTI_EDIT:

    @mcp.tool()
    async def multi_edit(
        edits: List[Dict],
        new_session: bool = False,
    ) -> str:
        """Edit multiple files by replacing exact string matches in a single batch.

        Performs targeted string replacements across multiple files in one call.
        Each edit specifies a file, old_string, and new_string. If one edit fails,
        remaining edits still proceed.

        🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
        call you made in this conversation (not a summary)?
           → NO or UNSURE: new_session=True is REQUIRED
           → YES, I see complete previous output: new_session=False is fine

        Missing this = missing AGENTS.md instruction files. When in doubt, always
        use new_session=True - it's safe.

        Args:
            edits: List of edit operations. Each dict must contain:
                - file_path (str): Path to the file relative to the base directory
                - old_string (str): Exact text to find and replace
                - new_string (str): Text to replace old_string with
                - replace_all (bool, optional): If True, replace all occurrences.
                  Defaults to False.
            new_session: Set True if you cannot see full output of a previous lineage
                         call in this conversation. Clears server caches so instruction
                         files are re-provided. Safe to use when uncertain.

        Returns:
            Combined results for all edits, with per-edit success/error messages.
        """
        return await multi_edit_file(edits, new_session)


if ENABLE_MULTI_READ:

    @mcp.tool()
    async def multi_read(
        file_paths: List[str],
        new_session: bool = False,
        show_line_numbers: bool = False,
    ) -> str:
        """Read the contents of multiple files in a single call (max 5).

        Reads up to 5 files at once, returning their contents with clear separators.
        Tracks all files for change detection and discovers instruction files.

        🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
        call you made in this conversation (not a summary)?
           → NO or UNSURE: new_session=True is REQUIRED
           → YES, I see complete previous output: new_session=False is fine

        Missing this = missing AGENTS.md instruction files. When in doubt, always
        use new_session=True - it's safe.

        Args:
            file_paths: List of file paths relative to the base directory (max 5).
            new_session: Set True if you cannot see full output of a previous lineage
                         call in this conversation. Clears server caches so instruction
                         files are re-provided. Safe to use when uncertain.
            show_line_numbers: If True, format output with line numbers (N→content).
                              Defaults to False.

        Returns:
            Combined file contents with per-file headers, [CHANGED_FILES] and
            [AGENTS.MD] sections appended at the end.
        """
        return await multi_read_file(file_paths, new_session, show_line_numbers)


@mcp.tool()
async def delete(file_path: str, new_session: bool = False) -> str:
    """Delete a file or empty directory.

    🛑 STOP AND CHECK: Can you see the FULL output of a previous lineage tool
    call you made in this conversation (not a summary)?
      → NO or UNSURE: new_session=True is REQUIRED
      → YES, I see complete previous output: new_session=False is fine

    Missing this = missing AGENTS.md instruction files. When in doubt, always
    use new_session=True - it's safe.

    Args:
        file_path: Path to the file relative to the base directory
        new_session: Set True if you cannot see full output of a previous lineage
                     call in this conversation. Clears server caches so instruction
                     files are re-provided. Safe to use when uncertain.

    Returns:
        Success or error message
    """
    return await delete_file(file_path, new_session)


@mcp.tool()
async def clear() -> str:
    """Clear all session caches.

    Resets file tracking and instruction file tracking
    (provided_folders). Use when instruction files need to be re-provided
    after context compaction.

    Alternative to using new_session=True on other tools.

    Returns:
        Success message confirming cache was cleared
    """
    return await clear_cache()


def main():
    """Entry point for CLI: lineage-mcp /path/to/base/dir

    This function is called when users run `lineage-mcp` from the command line
    after installing the package via pip. The base directory is already
    initialized from command-line arguments at module import time.
    """
    mcp.run()


if __name__ == "__main__":
    main()
