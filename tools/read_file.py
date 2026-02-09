"""Read file tool - file content reading with instruction file discovery."""

import bisect

from config import READ_CHAR_LIMIT
from file_watcher import format_changed_files_section
from instruction_files import (
    find_instruction_files_in_parents,
    include_instruction_file_content,
    mark_instruction_folder_if_applicable,
)
from path_utils import get_file_mtime_ms, resolve_path
from session_state import session


def paginate_content(
    content: str, page: int, char_limit: int
) -> tuple[str, int, int, int, int, bool]:
    """Paginate content with line-aware truncation.

    Args:
        content: Full file content
        page: Page number (0-indexed)
        char_limit: Maximum characters per page

    Returns:
        Tuple of:
        - page_content: Content for this page
        - actual_chars: Actual character count returned
        - start_line: 0-indexed starting line number
        - end_line: 0-indexed ending line number (exclusive)
        - total_pages: Total number of pages
        - is_last_page: Whether this is the final page
    """
    if not content:
        return "", 0, 0, 0, 1, True

    # Split into lines keeping newlines
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    # Calculate cumulative character positions at each line boundary
    # line_boundaries[i] = total chars up to and including line i (0-indexed)
    line_boundaries = []
    cumulative = 0
    for line in lines:
        cumulative += len(line)
        line_boundaries.append(cumulative)

    total_chars = line_boundaries[-1] if line_boundaries else 0

    # Calculate page boundaries
    page_start_char = page * char_limit
    page_end_char = (page + 1) * char_limit

    # Handle page beyond content
    if page_start_char >= total_chars:
        return (
            "",
            0,
            total_lines,
            total_lines,
            max(1, (total_chars + char_limit - 1) // char_limit),
            True,
        )

    # Find start line: which line contains page_start_char?
    # bisect_right returns insertion point after any existing entries
    start_line = bisect.bisect_right(line_boundaries, page_start_char)

    # Find end line: last line that ends at or before page_end_char
    end_line = bisect.bisect_right(line_boundaries, page_end_char)

    # Handle case where a single line exceeds the character limit
    line_start_pos = line_boundaries[start_line - 1] if start_line > 0 else 0
    line_end_pos = (
        line_boundaries[start_line] if start_line < total_lines else total_chars
    )
    current_line_length = line_end_pos - line_start_pos

    # If we're at the start of a line and that line alone exceeds the limit
    if page_start_char == line_start_pos and current_line_length > char_limit:
        # Force break within this line
        page_content = content[page_start_char : page_start_char + char_limit]
        actual_chars = len(page_content)
        end_line = start_line + 1  # Count this as covering one line
    elif start_line == end_line and start_line < total_lines:
        # We're in the middle of a line that exceeds the page boundary
        # Just take what we can from the current position
        take_chars = min(char_limit, line_end_pos - page_start_char)
        page_content = content[page_start_char : page_start_char + take_chars]
        actual_chars = len(page_content)
        end_line = start_line + 1
    else:
        # Normal line-aware truncation
        actual_start = line_boundaries[start_line - 1] if start_line > 0 else 0
        actual_end = (
            line_boundaries[min(end_line - 1, len(line_boundaries) - 1)]
            if end_line > 0
            else 0
        )
        page_content = content[actual_start:actual_end]
        actual_chars = len(page_content)

    # Calculate total pages
    total_pages = max(1, (total_chars + char_limit - 1) // char_limit)
    is_last_page = end_line >= total_lines

    return page_content, actual_chars, start_line, end_line, total_pages, is_last_page


async def read_file(
    file_path: str,
    new_session: bool = False,
    show_line_numbers: bool = False,
    offset: int | None = None,
    limit: int | None = None,
    page: int | None = None,
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
        page: Optional page number for character-based pagination (0-indexed).

    Returns:
        File contents with optional line numbers, [CHANGED_FILES] and instruction
        file sections appended.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.try_new_session()

    # Validate pagination parameters
    if page is not None and (offset is not None or limit is not None):
        return "Error: Cannot use 'page' with 'offset' or 'limit'. Choose one pagination method."

    if page is not None and page < 0:
        return f"Error: page must be non-negative, got {page}"

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

    # Determine if we need pagination:
    # - If page is explicitly provided, use pagination
    # - If no pagination params specified and file exceeds limit, use pagination
    # - Otherwise use offset/limit logic (backward compatibility)
    explicit_page = page is not None
    if page is None and offset is None and limit is None:
        # Check if file needs pagination based on size
        if len(full_content) > READ_CHAR_LIMIT:
            page = 0
            needs_pagination = True
        else:
            needs_pagination = False
    else:
        needs_pagination = page is not None

    if needs_pagination:
        # Use character-based pagination
        # page is guaranteed to be not None here (either explicitly provided or defaulted to 0)
        assert page is not None, "page should not be None when needs_pagination is True"
        page_content, actual_chars, start_line, end_line, total_pages, is_last = (
            paginate_content(full_content, page, READ_CHAR_LIMIT)
        )

        # Handle empty result (page beyond EOF)
        if not page_content and page > 0:
            return f"[Page {page + 1} of {total_pages}] File: {file_path}\n\nEnd of file reached."

        # Format with line numbers if requested
        if show_line_numbers:
            page_lines = page_content.splitlines(keepends=True)
            formatted_lines = []
            for i, line in enumerate(page_lines):
                line_num = start_line + i + 1  # 1-indexed
                line_content = line.rstrip("\n\r")
                formatted_lines.append(f"{line_num}→{line_content}")
            content = "\n".join(formatted_lines)
        else:
            content = page_content

        # Build pagination header
        output = f"[Page {page + 1} of {total_pages}, {actual_chars} chars] File: {file_path}\n"
        output += f"Showing lines {start_line + 1}-{end_line} of {total_lines}\n\n"
        output += content

        # Add continuation message if not last page
        if not is_last:
            output += f'\n\n---\nTo continue reading, use: read(file_path="{file_path}", page={page + 1})\n'
            output += f"(Next page starts at line {end_line + 1})"
        else:
            output += "\n\n---\nEnd of file reached."

    else:
        # Use existing offset/limit logic
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
