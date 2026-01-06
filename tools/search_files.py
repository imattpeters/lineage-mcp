"""Search files tool - glob pattern file search."""

from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_base_dir, resolve_path
from session_state import session


async def search_files(pattern: str, path: str = "", new_session: bool = False) -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern to search for (e.g., "*.txt", "src/**/*.py")
        path: Optional subdirectory to search within (relative to base directory)
        new_session: If True, clears all server caches before operation.

    Returns:
        List of matching file paths, or error message if pattern is invalid.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.clear()

    base_dir = get_base_dir()
    result = resolve_path(path)
    if not result.success:
        return result.error

    search_dir = result.path
    if not search_dir.exists():
        return f"Error: Directory not found: {path or '.'}"
    if not search_dir.is_dir():
        return f"Error: Path is not a directory: {path}"

    # Perform glob search
    matches: list[Path] = []
    for match in search_dir.glob(pattern):
        # Security: ensure match is still within base directory
        try:
            match.resolve().relative_to(base_dir.resolve())
            matches.append(match)
        except ValueError:
            continue

    if not matches:
        output = f"No files found matching pattern: {pattern}"
    else:
        lines = [f"Found {len(matches)} file(s) matching '{pattern}':", ""]
        for match in sorted(matches):
            rel_path = match.relative_to(base_dir)
            lines.append(f"- {rel_path}")
        output = "\n".join(lines)

    # Append changed files section
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\n{changed_section}"

    return output
