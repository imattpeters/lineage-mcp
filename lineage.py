"""Lineage MCP - Entry point and tool registration.

A Model Context Protocol server for file operations with change detection
and instruction file discovery.
"""

import sys
from typing import Dict, List

from mcp.server.fastmcp import Context, FastMCP

from config import ALLOW_FULL_PATHS, DEBUG_CLIENT_INFO, ENABLE_MULTI_EDIT, INTERRUPT_MESSAGE, get_read_char_limit
from path_utils import init_base_dir_from_args, set_allow_full_paths
from session_state import session
from tools import (
    clear_cache,
    delete_file,
    edit_file,
    list_files,
    multi_edit_file,
    read_file,
    search_files,
    write_file,
)
from tray_client import init_tray_client, update_tray_files_tracked, update_tray_first_call

# Initialize base directory from command line argument
init_base_dir_from_args()

# Apply allowFullPaths setting from config
set_allow_full_paths(ALLOW_FULL_PATHS)

# Try to connect to the system tray (optional, non-blocking)
try:
    from path_utils import get_base_dir
    init_tray_client(str(get_base_dir()))
except Exception:
    pass  # Tray is optional — never fail the server

# Create MCP server instance
mcp = FastMCP("lineage")

def _get_client_name(ctx: Context | None) -> str | None:
    """Extract the MCP client name from the Context, if available."""
    try:
        if ctx and ctx.session and ctx.session.client_params:
            return ctx.session.client_params.clientInfo.name
    except (AttributeError, TypeError):
        pass
    return None

def _check_interrupted() -> str | None:
    """Check if the session is in interrupted mode.

    When interrupted, tools must return ONLY the interrupt message and
    perform NO other operations. The interrupted state persists until
    the user clicks Resume in the system tray.

    Returns:
        The configured interrupt message if interrupted, None otherwise.
    """
    if session.check_interrupted():
        return INTERRUPT_MESSAGE
    return None

def _tray_notify_tool_call(
    tool_name: str, args_summary: str, ctx: Context | None = None
) -> None:
    """Notify the tray about a tool call (first call captures client info).

    Also updates the files tracked count.

    Args:
        tool_name: Name of the tool being called.
        args_summary: Brief summary of tool arguments.
        ctx: MCP Context, if available.
    """
    try:
        client_name = _get_client_name(ctx)
        update_tray_first_call(tool_name, args_summary, client_name)
        update_tray_files_tracked(len(session.mtimes), tool_name, args_summary)
    except Exception:
        pass  # Tray updates are best-effort

# Register tools with MCP server
@mcp.tool()
async def list(path: str = "", ctx: Context = None) -> str:
    """List all files in the specified directory.

    Args:
        path: Optional subdirectory path relative to the base directory

    Returns:
        Markdown formatted table of files/directories with metadata and changed files section.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("list", path, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await list_files(path)
    update_tray_files_tracked(len(session.mtimes))
    return result

@mcp.tool()
async def search(pattern: str, path: str = "", ctx: Context = None) -> str:
    """Search for files matching a glob pattern.

    Searches for files using glob patterns (e.g., "*.txt", "**/*.py", "src/*/config.json").
    Supports recursive patterns with ** syntax. Returns list of matching file paths
    relative to the base directory.

    Args:
        pattern: Glob pattern to search for (e.g., "*.txt", "src/**/*.py")
        path: Optional subdirectory to search within (relative to base directory)

    Returns:
        List of matching file paths, or error message if pattern is invalid.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("search", pattern, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await search_files(pattern, path)
    return result

@mcp.tool()
async def read(
    file_path: str,
    show_line_numbers: bool = False,
    offset: int | None = None,
    limit: int | None = None,
    cursor: int | None = None,
    ctx: Context = None,
) -> str:
    """Read the contents of a file.

    Tracks file modification time for change detection [on subsequent reads you
    will be notified of file changes to file you've read] and discovers AGENTS.md
    files from parent directories and appends them to the read.

    Supports two pagination methods:
    1. Line-based: Use offset and limit for specific line ranges
    2. Character-based: Use cursor for automatic pagination with overhead-aware budgeting

    When a file exceeds the character limit (default 50,000), it is automatically
    paginated. Each read returns complete lines and a cursor value for the next call.

    Args:
        file_path: Path to the file relative to the base directory
        show_line_numbers: If True, format output with line numbers (N→content). Defaults to False.
        offset: Optional 0-based line number to start reading from. If None, starts at line 0.
                If offset >= total lines, returns empty result.
                Cannot be used with 'cursor' parameter.
        limit: Optional number of lines to read. If None, reads to end of file.
               If limit=0 or offset beyond EOF, returns empty result.
               Cannot be used with 'cursor' parameter.
        cursor: Optional character offset for cursor-based pagination.
                Use the cursor value from a previous response to continue reading.
                The response includes the exact cursor value to pass for the next read.
                Cannot be used with 'offset' or 'limit' parameters.

    Returns:
        File contents (full or partial) with optional line numbers.
        For paginated reads: includes progress info, line range, reads remaining,
        and continuation instructions with the next cursor value.
        [CHANGED_FILES] and [AGENTS.MD] sections appended as usual.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("read", file_path, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    client_name = _get_client_name(ctx)
    char_limit = get_read_char_limit(client_name)

    result = await read_file(
        file_path, show_line_numbers, offset, limit, cursor, char_limit
    )

    if DEBUG_CLIENT_INFO:
        debug_prefix = f"[Client: {client_name or 'unknown'} | readCharLimit: {char_limit}]\n"
        result = debug_prefix + result

    update_tray_files_tracked(len(session.mtimes))
    return result

@mcp.tool()
async def write(file_path: str, content: str, ctx: Context = None) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file relative to the base directory
        content: Content to write to the file

    Returns:
        Success or error message.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("write", file_path, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await write_file(file_path, content)
    update_tray_files_tracked(len(session.mtimes))
    return result

@mcp.tool()
async def edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    ctx: Context = None,
) -> str:
    """Edit a file by replacing exact string matches.

    Performs targeted string replacements in a file. The old_string must exist
    in the file and be unique (unless replace_all is True).

    Args:
        file_path: Path to the file relative to the base directory
        old_string: Exact text to find and replace (must match exactly including whitespace)
        new_string: Text to replace old_string with
        replace_all: If True, replace all occurrences; if False, old_string must be unique

    Returns:
        Success message with replacement count, or error message.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("edit", file_path, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await edit_file(file_path, old_string, new_string, replace_all)
    update_tray_files_tracked(len(session.mtimes))
    return result

if ENABLE_MULTI_EDIT:

    @mcp.tool()
    async def multi_edit(
        edits: List[Dict],
        ctx: Context = None,
    ) -> str:
        """Edit multiple files by replacing exact string matches in a single batch.

        Performs targeted string replacements across multiple files in one call.
        Each edit specifies a file, old_string, and new_string. If one edit fails,
        remaining edits still proceed.

        Args:
            edits: List of edit operations. Each dict must contain:
                - file_path (str): Path to the file relative to the base directory
                - old_string (str): Exact text to find and replace
                - new_string (str): Text to replace old_string with
                - replace_all (bool, optional): If True, replace all occurrences.
                  Defaults to False.

        Returns:
            Combined results for all edits, with per-edit success/error messages.
            If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
            operations immediately and use ask_user() before proceeding.
        """
        _tray_notify_tool_call("multi_edit", f"{len(edits)} edits", ctx)
        interrupted = _check_interrupted()
        if interrupted:
            return interrupted
        result = await multi_edit_file(edits)
        update_tray_files_tracked(len(session.mtimes))
        return result


@mcp.tool()
async def delete(file_path: str, ctx: Context = None) -> str:
    """Delete a file or empty directory.

    Args:
        file_path: Path to the file relative to the base directory

    Returns:
        Success or error message.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    _tray_notify_tool_call("delete", file_path, ctx)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await delete_file(file_path)
    update_tray_files_tracked(len(session.mtimes))
    return result


@mcp.tool()
async def clear() -> str:
    """Clear all session caches.

    Resets file tracking and instruction file tracking
    (provided_folders). Use when instruction files need to be re-provided
    after context compaction.

    Cache is also cleared automatically via the system tray or precompact hooks.

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
