"""List files tool - directory listing with markdown table output."""

from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_base_dir, resolve_path
from session_state import session


async def list_files(path: str = "", new_session: bool = False) -> str:
    """List all files in the specified directory.

    Args:
        path: Optional subdirectory path relative to the base directory
        new_session: If True, clears all server caches before operation.

    Returns:
        Markdown formatted table of files/directories with metadata and changed files section.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.try_new_session()

    base_dir = get_base_dir()
    result = resolve_path(path)
    if not result.success:
        return result.error

    full_path = result.path
    if not full_path.exists():
        return f"Error: Directory not found: {path or '.'}"
    if not full_path.is_dir():
        return f"Error: Path is not a directory: {path}"

    # Build file listing
    entries = sorted(full_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = ["| Name | Type | Size |", "|------|------|------|"]

    for entry in entries:
        try:
            rel_path = entry.relative_to(base_dir)
            if entry.is_dir():
                lines.append(f"| {rel_path}/ | 📁 dir | - |")
            else:
                size = entry.stat().st_size
                lines.append(f"| {rel_path} | 📄 file | {size:,} bytes |")
        except (OSError, ValueError):
            continue

    output = "\n".join(lines)

    # Append changed files section
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\n{changed_section}"

    return output
