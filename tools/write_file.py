"""Write file tool - create or overwrite files."""

from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_file_mtime_ms, resolve_path
from session_state import session


async def write_file(file_path: str, content: str) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file relative to the base directory
        content: Content to write to the file

    Returns:
        Success or error message
    """
    result = resolve_path(file_path)
    if not result.success:
        return result.error

    full_path = result.path

    try:
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        # Track file for change detection (LLM writes are not "external changes")
        file_path_str = str(full_path)
        mtime = get_file_mtime_ms(full_path)
        session.track_file(file_path_str, mtime, content)

        output = f"Successfully wrote to {file_path}"

        # Append changed files section
        changed_section = format_changed_files_section()
        if changed_section:
            output += f"\n\n{changed_section}"

        return output
    except OSError as e:
        return f"Error writing file: {e}"
