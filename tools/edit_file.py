"""Edit file tool - string replacement in files."""

from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_base_dir, get_file_mtime_ms, resolve_path
from session_state import session


async def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """Edit a file by replacing exact string matches.

    Args:
        file_path: Path to the file relative to the base directory
        old_string: Exact text to find and replace (must match exactly including whitespace)
        new_string: Text to replace old_string with
        replace_all: If True, replace all occurrences; if False, old_string must be unique

    Returns:
        Success message with replacement count, or error message
    """
    result = resolve_path(file_path)
    if not result.success:
        return result.error

    full_path = result.path
    if not full_path.exists():
        return f"Error: File not found: {file_path} (base directory: {get_base_dir()})"
    if not full_path.is_file():
        return f"Error: Path is not a file: {file_path} (base directory: {get_base_dir()})"

    try:
        content = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"Error reading file: {e}"

    # Count occurrences
    count = content.count(old_string)
    if count == 0:
        return f"Error: String not found in file"

    if not replace_all and count > 1:
        return f"Error: String found {count} times. Use replace_all=True to replace all, or make the string more specific."

    # Perform replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    try:
        full_path.write_text(new_content, encoding="utf-8")

        # Track file for change detection (LLM edits are not "external changes")
        file_path_str = str(full_path)
        mtime = get_file_mtime_ms(full_path)
        session.track_file(file_path_str, mtime, new_content)

        output = f"Successfully replaced {count} occurrence(s) in {file_path}"

        # Append changed files section
        changed_section = format_changed_files_section()
        if changed_section:
            output += f"\n\n{changed_section}"

        return output
    except OSError as e:
        return f"Error writing file: {e}"
