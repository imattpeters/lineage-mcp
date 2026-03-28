"""Search files tool - glob pattern file search."""

import asyncio
from pathlib import Path

from file_watcher import format_changed_files_section
from path_utils import get_allow_full_paths, get_base_dir, resolve_path


async def search_files(pattern: str, path: str = "") -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern to search for (e.g., "*.txt", "src/**/*.py")
        path: Optional subdirectory to search within (relative to base directory)

    Returns:
        List of matching file paths, or error message if pattern is invalid.
    """
    base_dir = get_base_dir()
    result = resolve_path(path)
    if not result.success:
        return result.error

    search_dir = result.path
    if not search_dir.exists():
        return f"Error: Directory not found: {path or '.'} (base directory: {get_base_dir()})"
    if not search_dir.is_dir():
        return f"Error: Path is not a directory: {path} (base directory: {get_base_dir()})"

    # Perform glob search in a thread pool to avoid blocking
    def do_glob():
        matches: list[Path] = []
        for match in search_dir.glob(pattern):
            resolved = match.resolve()
            # Security: only allow results outside base_dir when allowFullPaths is enabled
            if not get_allow_full_paths():
                try:
                    resolved.relative_to(base_dir.resolve())
                except ValueError:
                    continue
            matches.append(match)
        return matches

    matches = await asyncio.to_thread(do_glob)

    if not matches:
        output = f"No files found matching pattern: {pattern}"
    else:
        lines = [f"Found {len(matches)} file(s) matching '{pattern}':", ""]
        for match in sorted(matches):
            try:
                display_path = match.relative_to(base_dir)
            except ValueError:
                display_path = match
            lines.append(f"- {display_path}")
        output = "\n".join(lines)

    # Append changed files section
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\nEOF\n[Lineage Message]:{changed_section}"

    return output
