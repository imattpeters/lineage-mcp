"""Read file tool - file content reading with instruction file discovery."""

from file_watcher import format_changed_files_section
from instruction_files import (
    find_instruction_files_in_parents,
    include_instruction_file_content,
    mark_instruction_folder_if_applicable,
)
from path_utils import get_file_mtime_ms, resolve_path
from session_state import session


async def read_file(
    file_path: str,
    new_session: bool = False,
    show_line_numbers: bool = False,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read the contents of a file.

    Tracks file modification time for change detection and discovers AGENTS.md
    files from parent directories.

    Args:
        file_path: Path to the file relative to the base directory
        new_session: If True, clears all server caches before operation.
        show_line_numbers: If True, format output with line numbers (N→content).
        offset: Optional 0-based line number to start reading from.
        limit: Optional number of lines to read.

    Returns:
        File contents with optional line numbers, [CHANGED_FILES] and instruction
        file sections appended.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.clear()

    # Validate offset/limit
    if offset is not None and offset < 0:
        return f"Error: offset must be non-negative, got {offset}"
    if limit is not None and limit < 0:
        return f"Error: limit must be non-negative, got {limit}"

    result = resolve_path(file_path)
    if not result.success:
        return result.error

    full_path = result.path
    if not full_path.exists():
        return f"Error: File not found: {file_path}"
    if not full_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    # Read full file content once
    try:
        full_content = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading file: {e}"

    lines = full_content.splitlines(keepends=True)
    total_lines = len(lines)

    # Apply offset and limit
    start_line = offset if offset is not None else 0
    if start_line >= total_lines:
        # Offset beyond EOF
        content = ""
        displayed_lines: list[str] = []
    else:
        end_line = total_lines
        if limit is not None:
            end_line = min(start_line + limit, total_lines)
        displayed_lines = lines[start_line:end_line]
        content = "".join(displayed_lines)

    # Format with line numbers if requested
    if show_line_numbers and displayed_lines:
        formatted_lines = []
        for i, line in enumerate(displayed_lines):
            line_num = start_line + i + 1  # 1-based line numbers
            # Remove trailing newline for formatting, add back after
            line_content = line.rstrip("\n\r")
            formatted_lines.append(f"{line_num}→{line_content}")
        content = "\n".join(formatted_lines)

    output = content

    # Track file for change detection (always track full content)
    file_path_str = str(full_path)
    mtime = get_file_mtime_ms(full_path)
    session.track_file(file_path_str, mtime, full_content)

    # Mark instruction folder if this is an instruction file read directly
    mark_instruction_folder_if_applicable(full_path)

    # Append changed files section
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\n{changed_section}"

    # Discover and append instruction files from parent directories
    instruction_files = find_instruction_files_in_parents(full_path)
    instruction_content = include_instruction_file_content(instruction_files)
    if instruction_content:
        output += f"\n\n{instruction_content}"

    return output
