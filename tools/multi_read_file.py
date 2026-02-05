"""Multi-read file tool - batch file reading."""

from file_watcher import format_changed_files_section
from instruction_files import (
    find_instruction_files_in_parents,
    include_instruction_file_content,
    mark_instruction_folder_if_applicable,
)
from path_utils import get_file_mtime_ms, resolve_path
from session_state import session

MAX_FILES = 5


async def multi_read_file(
    file_paths: list[str],
    new_session: bool = False,
    show_line_numbers: bool = False,
) -> str:
    """Read the contents of multiple files in a single call.

    Reads up to 5 files at once, returning their contents separated by clear
    headers. Tracks all files for change detection and discovers instruction
    files from parent directories.

    Args:
        file_paths: List of file paths relative to the base directory (max 5).
        new_session: If True, clears all server caches before operation.
        show_line_numbers: If True, format output with line numbers (N→content).

    Returns:
        Combined file contents with per-file headers, [CHANGED_FILES] and
        instruction file sections appended at the end.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.try_new_session()

    if not file_paths:
        return "Error: No file paths provided"

    if len(file_paths) > MAX_FILES:
        return f"Error: Too many files requested ({len(file_paths)}). Maximum is {MAX_FILES}."

    sections: list[str] = []
    all_instruction_files: list = []

    for file_path in file_paths:
        header = f"--- {file_path} ---"

        result = resolve_path(file_path)
        if not result.success:
            sections.append(f"{header}\n{result.error}")
            continue

        full_path = result.path
        if not full_path.exists():
            sections.append(f"{header}\nError: File not found: {file_path}")
            continue
        if not full_path.is_file():
            sections.append(f"{header}\nError: Path is not a file: {file_path}")
            continue

        # Read file content
        try:
            full_content = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            sections.append(f"{header}\nError reading file: {e}")
            continue

        lines = full_content.splitlines(keepends=True)

        # Format with line numbers if requested
        if show_line_numbers and lines:
            formatted_lines = []
            for i, line in enumerate(lines):
                line_num = i + 1  # 1-based line numbers
                line_content = line.rstrip("\n\r")
                formatted_lines.append(f"{line_num}→{line_content}")
            content = "\n".join(formatted_lines)
        else:
            content = full_content

        sections.append(f"{header}\n{content}")

        # Track file for change detection
        file_path_str = str(full_path)
        mtime = get_file_mtime_ms(full_path)
        session.track_file(file_path_str, mtime, full_content)

        # Mark instruction folder if this is an instruction file read directly
        mark_instruction_folder_if_applicable(full_path)

        # Collect instruction files from parent directories
        instruction_files = find_instruction_files_in_parents(full_path)
        for instr_file in instruction_files:
            if instr_file not in all_instruction_files:
                all_instruction_files.append(instr_file)

    output = "\n\n".join(sections)

    # Append changed files section (once at end)
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\n{changed_section}"

    # Append instruction file content (once at end, deduplicated)
    instruction_content = include_instruction_file_content(all_instruction_files)
    if instruction_content:
        output += f"\n\n{instruction_content}"

    return output
