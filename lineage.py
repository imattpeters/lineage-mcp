"""Lineage MCP - Entry point and tool registration.

A Model Context Protocol server for file operations with change detection
and instruction file discovery.
"""

import sys
from typing import Dict, List

from mcp.server.fastmcp import Context, FastMCP

from config import ALLOW_FULL_PATHS, DEBUG_CLIENT_INFO, INTERRUPT_MESSAGE, get_read_char_limit, get_response_footer
from path_utils import init_base_dir_from_args, set_allow_full_paths
from session_state import session
from tools import (
    clear_cache,
    delete_file,
    list_files,
    modify as modify_impl,
    read_file,
    search_files,
)
from tray_client import init_tray_client, log_tool_call

# Initialize base directory from command line argument
init_base_dir_from_args()

# Apply allowFullPaths setting from config
set_allow_full_paths(ALLOW_FULL_PATHS)

# Try to connect to the system tray (optional, non-blocking)
try:
    from path_utils import get_base_dir
    init_tray_client(str(get_base_dir()))
except Exception:
    pass  # Tray is optional - never fail the server

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

def _append_footer(result: str, client_name: str | None = None) -> str:
    """Append the configured responseFooter to a tool result, if non-empty."""
    footer = get_response_footer(client_name)
    if not footer:
        return result
    return result + "\n\n---\n" + footer


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
    log_tool_call("list", ctx=ctx, path=path)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await list_files(path)
    return _append_footer(result, _get_client_name(ctx))

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
    log_tool_call("search", ctx=ctx, pattern=pattern, path=path)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await search_files(pattern, path)
    return _append_footer(result, _get_client_name(ctx))

@mcp.tool()
async def read(
    file_path: str,
    show_line_numbers: bool = False,
    offset: int | str | None = None,
    limit: int | str | None = None,
    cursor: int | str | None = None,
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
    def _coerce_int(name: str, value: int | str | None) -> int | None:
        if value is None or isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"'{name}' must be an integer, got: {value!r}")

    offset = _coerce_int("offset", offset)
    limit = _coerce_int("limit", limit)
    cursor = _coerce_int("cursor", cursor)

    log_tool_call("read", ctx=ctx, file_path=file_path,
                  show_line_numbers=show_line_numbers,
                  offset=offset, limit=limit, cursor=cursor)
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

    return _append_footer(result, client_name)

@mcp.tool()
async def modify(
    operations: List[Dict],
    on_error: str = "abort",
    ctx: Context = None,
) -> str:
    """Modify one or more text files by creating, overwriting, appending, or replacing exact text.

    Use this as the single tool for file content changes. Provide an ordered list of
    operations. Each operation chooses its behavior with the required `operation` field.

    Operation types:
    - create: create a new file with `text`; fails if the file already exists
    - overwrite: replace the entire file with `text`; creates the file if needed
    - append: add `text` to the end of an existing file
    - replace: replace exact `match_text` with `text`

    Operations run sequentially in the order provided. Later operations see the results
    of earlier ones, including earlier operations on the same file.

    Args:
        operations: Ordered list of file modification operations. Each operation must include:
            - file_path (str): Path to the file relative to the base directory
            - operation (str): One of 'create', 'overwrite', 'append', or 'replace'
            - text (str): Content to write, append, or use as replacement text
            - match_text (str, optional): Exact text to find when operation='replace'
            - occurrence (str, optional): 'one' or 'all' for replace operations. Defaults to 'one'.
        on_error: 'abort' to stop at the first failure, or 'continue' to keep processing later operations.
                  Defaults to 'abort'. Earlier successful operations are not rolled back.

    Returns:
        Per-operation success or error results.
        If you receive a "[SYSTEM] MCP Tool Interrupt Active" message, you MUST stop all
        operations immediately and use ask_user() before proceeding.
    """
    log_tool_call("modify", ctx=ctx, operations=operations, on_error=on_error)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await modify_impl(operations, on_error)
    return _append_footer(result, _get_client_name(ctx))


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
    log_tool_call("delete", ctx=ctx, file_path=file_path)
    interrupted = _check_interrupted()
    if interrupted:
        return interrupted
    result = await delete_file(file_path)
    return _append_footer(result, _get_client_name(ctx))


@mcp.tool()
async def clear(ctx: Context = None) -> str:
    """Clear all session caches.

    Resets file tracking and instruction file tracking
    (provided_folders). Use when instruction files need to be re-provided
    after context compaction.

    Cache is also cleared automatically via the system tray or client hooks (SessionStart, PreCompact).

    Returns:
        Success message confirming cache was cleared
    """
    result = await clear_cache()
    return _append_footer(result, _get_client_name(ctx))

def main():
    """Entry point for CLI: lineage-mcp /path/to/base/dir

    This function is called when users run `lineage-mcp` from the command line
    after installing the package via pip. The base directory is already
    initialized from command-line arguments at module import time.
    """
    mcp.run()

if __name__ == "__main__":
    main()
