"""Delete file tool - delete files or empty directories."""

from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_base_dir, resolve_path
from session_state import session


async def delete_file(file_path: str) -> str:
    """Delete a file or empty directory.

    Args:
        file_path: Path to the file relative to the base directory

    Returns:
        Success or error message
    """
    result = resolve_path(file_path)
    if not result.success:
        return result.error

    full_path = result.path
    if not full_path.exists():
        return f"Error: File not found: {file_path} (base directory: {get_base_dir()})"

    try:
        file_path_str = str(full_path)
        if full_path.is_dir():
            full_path.rmdir()  # Only works on empty directories
            output = f"Successfully deleted empty directory: {file_path}"
        else:
            full_path.unlink()
            output = f"Successfully deleted file: {file_path}"

        # Remove from tracking
        session.untrack_file(file_path_str)

        # Append changed files section
        changed_section = format_changed_files_section()
        if changed_section:
            output += f"\n\n{changed_section}"

        return output
    except OSError as e:
        return f"Error deleting file: {e}"
