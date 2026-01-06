"""Lineage MCP - Entry point and tool registration.

A Model Context Protocol server for file operations with change detection
and instruction file discovery.
"""

import sys

from mcp.server.fastmcp import FastMCP

from path_utils import init_base_dir_from_args
from tools import clear_cache, delete_file, edit_file, list_files, read_file, search_files, write_file

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
) -> str:
    """Read the contents of a file.

    Tracks file modification time for change detection [on subsequent reads you
    will be notified of file changes to file you've read] and discovers AGENTS.md
    files from parent directories and appends them to the read.

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
        limit: Optional number of lines to read. If None, reads to end of file.
               If limit=0 or offset beyond EOF, returns empty result.

    Returns:
        File contents (full or partial based on offset/limit) with optional line numbers,
        [CHANGED_FILES] and [AGENTS.MD] sections appended. Returns empty result if offset
        is beyond end of file.
    """
    return await read_file(file_path, new_session, show_line_numbers, offset, limit)


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


if __name__ == "__main__":
    mcp.run()
