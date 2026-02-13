"""Read file tool - file content reading with cursor-based pagination."""

import math

from config import READ_CHAR_LIMIT
from file_watcher import format_changed_files_section
from instruction_files import (
    find_instruction_files_in_parents,
    include_instruction_file_content,
    mark_instruction_folder_if_applicable,
)
from path_utils import get_base_dir, get_file_mtime_ms, resolve_path
from session_state import session


def extract_content_by_cursor(
    content: str,
    cursor: int,
    budget: int,
    show_line_numbers: bool = False,
) -> tuple[str, int, int, int, int]:
    """Extract content from a character cursor position within a budget.

    Line-aware extraction: never splits mid-line. When show_line_numbers is True,
    the line number prefix cost (e.g. "481→") is counted against the budget.

    Args:
        content: Full file content
        cursor: Character offset to start from (0-indexed)
        budget: Maximum characters for the extracted content (including line number prefixes)
        show_line_numbers: If True, account for line number prefix cost in budget

    Returns:
        Tuple of:
        - extracted: The extracted content (formatted with line numbers if enabled)
        - next_cursor: Character offset where the next read should start
        - start_line: 0-indexed starting line number
        - end_line: 0-indexed ending line number (exclusive)
        - total_lines: Total number of lines in the file
    """
    if not content:
        return "", 0, 0, 0, 0

    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    # Build cumulative character positions
    line_boundaries: list[int] = []
    cumulative = 0
    for line in lines:
        cumulative += len(line)
        line_boundaries.append(cumulative)

    total_chars = line_boundaries[-1] if line_boundaries else 0

    # Cursor beyond content
    if cursor >= total_chars:
        return "", total_chars, total_lines, total_lines, total_lines

    # Find which line the cursor falls in
    # Snap cursor to the start of its containing line
    start_line = 0
    for i, boundary in enumerate(line_boundaries):
        if cursor < boundary:
            start_line = i
            break
    # Actual start position (beginning of the start_line)
    actual_start = line_boundaries[start_line - 1] if start_line > 0 else 0

    # Accumulate lines within budget
    accumulated = 0
    end_line = start_line
    formatted_parts: list[str] = []

    for i in range(start_line, total_lines):
        line = lines[i]
        line_content = line.rstrip("\n\r")

        if show_line_numbers:
            line_num = i + 1  # 1-indexed
            prefix = f"{line_num}→"
            display_line = f"{prefix}{line_content}"
            line_cost = len(display_line) + 1  # +1 for the joining newline
        else:
            display_line = line_content
            # Cost is the raw line length (including its original newline)
            line_cost = len(line)

        # Check if adding this line would exceed the budget
        if accumulated + line_cost > budget and accumulated > 0:
            # Stop before this line (but always include at least one line)
            break

        if show_line_numbers:
            formatted_parts.append(display_line)
            accumulated += line_cost
        else:
            accumulated += line_cost

        end_line = i + 1  # exclusive

    # Build extracted content
    if show_line_numbers:
        extracted = "\n".join(formatted_parts)
    else:
        actual_end = line_boundaries[end_line - 1] if end_line > 0 else 0
        extracted = content[actual_start:actual_end]

    # Next cursor is the char position after the last included line
    next_cursor = line_boundaries[end_line - 1] if end_line > 0 else 0

    return extracted, next_cursor, start_line, end_line, total_lines


async def read_file(
    file_path: str,
    new_session: bool = False,
    show_line_numbers: bool = False,
    offset: int | None = None,
    limit: int | None = None,
    cursor: int | None = None,
    read_char_limit: int | None = None,
) -> str:
    """Read the contents of a file.

    Tracks file modification time for change detection and discovers AGENTS.md
    files from parent directories.

    Supports two pagination methods:
    1. Line-based: Use offset and limit for specific line ranges
    2. Character-based: Use cursor for automatic pagination with overhead-aware budgeting

    When a file exceeds the character limit (default 50,000), it is automatically
    paginated. Each read returns complete lines and a cursor value for the next call.

    Args:
        file_path: Path to the file relative to the base directory
        new_session: If True, clears all server caches before operation.
        show_line_numbers: If True, format output with line numbers (N→content).
        offset: Optional 0-based line number to start reading from.
        limit: Optional number of lines to read.
        cursor: Optional character offset for cursor-based pagination.
                Use the cursor value from a previous response to continue reading.
        read_char_limit: Optional character limit override. If None, uses the
                         global READ_CHAR_LIMIT from config.

    Returns:
        File contents with optional line numbers, [CHANGED_FILES] and instruction
        file sections appended.
    """
    # Use provided limit or fall back to global config
    effective_char_limit = read_char_limit if read_char_limit is not None else READ_CHAR_LIMIT
    # Handle new_session - clear all caches
    if new_session:
        session.try_new_session()

    # Validate pagination parameters
    if cursor is not None and (offset is not None or limit is not None):
        return "Error: Cannot use 'cursor' with 'offset' or 'limit'. Choose one pagination method."

    if cursor is not None and cursor < 0:
        return f"Error: cursor must be non-negative, got {cursor}"

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
        return f"Error: File not found: {file_path} (base directory: {get_base_dir()})"
    if not full_path.is_file():
        return f"Error: Path is not a file: {file_path} (base directory: {get_base_dir()})"

    # Read full file content once
    try:
        full_content = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading file: {e}"

    lines = full_content.splitlines(keepends=True)
    total_lines = len(lines)
    total_chars = len(full_content)

    # Track file for change detection (always track full content)
    file_path_str = str(full_path)
    mtime = get_file_mtime_ms(full_path)
    session.track_file(file_path_str, mtime, full_content)

    # Mark instruction folder if this is an instruction file read directly
    mark_instruction_folder_if_applicable(full_path)

    # Pre-generate overhead sections (needed for budget calculation)
    changed_section = format_changed_files_section()
    instruction_files = find_instruction_files_in_parents(full_path)
    instruction_content = include_instruction_file_content(instruction_files)

    overhead = ""
    if changed_section:
        overhead += f"\n\n---\n{changed_section}"
    if instruction_content:
        overhead += f"\n\n---\n{instruction_content}"
    overhead_size = len(overhead)

    # Determine if we need cursor-based pagination
    if cursor is not None:
        needs_cursor_pagination = True
    elif offset is None and limit is None:
        # Auto-detect: will the total output exceed the limit?
        total_output_estimate = total_chars + overhead_size + 300  # rough header/footer
        needs_cursor_pagination = total_output_estimate > effective_char_limit
        if needs_cursor_pagination:
            cursor = 0
    else:
        needs_cursor_pagination = False

    if needs_cursor_pagination:
        assert cursor is not None

        # Handle cursor at or beyond EOF
        if cursor >= total_chars:
            output = f"File: {file_path}\n\nEnd of file reached."
            output += overhead
            return output

        # Calculate content budget: total limit minus overhead minus header/footer estimate
        # We'll calculate the actual header/footer after extraction, but the size is predictable
        header_footer_estimate = 200 + len(file_path) * 2  # conservative
        content_budget = effective_char_limit - overhead_size - header_footer_estimate

        # Always allow at least some content (at minimum one line)
        # If budget goes negative due to large overhead, we still show at least one line
        # and accept going over the limit
        content_budget = max(content_budget, 1)

        # Extract content within budget
        extracted, next_cursor, start_line, end_line, _ = extract_content_by_cursor(
            full_content, cursor, content_budget, show_line_numbers
        )

        is_last = next_cursor >= total_chars

        # Calculate reads remaining
        if is_last:
            reads_remaining = 0
        else:
            remaining_chars = total_chars - next_cursor
            reads_remaining = math.ceil(remaining_chars / effective_char_limit)

        # Calculate percentage of file in this response
        chunk_size = next_cursor - cursor
        percent_of_file = int((chunk_size / total_chars) * 100) if total_chars > 0 else 100

        # Build header
        if is_last:
            header = f"[chars {cursor}-{next_cursor} of {total_chars} ({percent_of_file}% of file)] File: {file_path}\n"
        else:
            header = f"[chars {cursor}-{next_cursor} of {total_chars} ({percent_of_file}% of file), ~{reads_remaining} reads remaining] File: {file_path}\n"
        header += f"Showing lines {start_line + 1}-{end_line} of {total_lines}\n\n"

        output = header + extracted

        # Build continuation/EOF footer (appended AFTER overhead so it's the last thing)
        if not is_last:
            continuation = f'\n\n---\nTo continue reading, use: read(file_path="{file_path}", cursor={next_cursor})'
            continuation += f"\n(~{reads_remaining} reads remaining, next starts at line {end_line + 1})"
        else:
            continuation = "\n\n---\nEnd of file reached."

    else:
        # Use existing offset/limit logic (no cursor pagination)
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
        continuation = ""

    # Append pre-generated overhead
    output += overhead

    # Append continuation/EOF message last (so it's the final thing the LLM sees)
    output += continuation

    return output
