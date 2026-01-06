"""File change detection for the MCP file server.

Provides line-level diff tracking to detect external modifications.
"""

from difflib import unified_diff
from pathlib import Path
from typing import Any, Dict, List

from path_utils import get_file_mtime_ms
from session_state import session


def calculate_changed_line_ranges(old_content: str, new_content: str) -> str:
    """Calculate which line ranges changed between two versions.

    Uses difflib to identify changed lines and returns ranges like "5-8,15-20".

    Args:
        old_content: Previous file content.
        new_content: Current file content.

    Returns:
        String with changed line ranges (e.g. "5-8,15-20") or "1-EOF" if diff fails.
    """
    if not old_content and not new_content:
        return "1-EOF"

    try:
        old_lines = old_content.splitlines(keepends=False)
        new_lines = new_content.splitlines(keepends=False)

        # Generate unified diff
        diff = list(unified_diff(old_lines, new_lines, lineterm="", n=0))

        # Extract line numbers from diff output
        current_start: int | None = None
        current_end: int | None = None

        for line in diff:
            if line.startswith("@@"):
                # Parse line numbers from @@ -a,b +c,d @@
                try:
                    parts = line.split()[2]  # Get +c,d part
                    line_info = parts.split(",")[0].lstrip("+")
                    line_num = int(line_info)

                    if current_start is None:
                        current_start = line_num
                    current_end = line_num
                except (ValueError, IndexError):
                    continue
            elif line.startswith("+") or line.startswith("-"):
                # Track that this is part of a changed region
                if current_start is not None:
                    current_end = (current_end or current_start) + 1

        # Combine overlapping or adjacent ranges
        if current_start is not None and current_end is not None:
            return f"{current_start}-{current_end}"

        # If no specific changes detected, report all lines
        return f"1-{len(new_lines)}" if new_lines else "1-EOF"

    except Exception:
        # Fallback to simple "entire file" if diff fails
        return "1-EOF"


def get_changed_files() -> List[Dict[str, Any]]:
    """Get list of files that have changed since last read.

    Compares current modification times and content against stored values for
    all tracked files. Uses line-level diffing to identify changed ranges.

    Returns:
        List of dicts with 'path', 'status', 'changedLineRanges', and 'secondsAgo'.
        Empty list if no files have changed.
    """
    changed: List[Dict[str, Any]] = []

    for tracked_path, old_mtime in list(session.mtimes.items()):
        file_path = Path(tracked_path)

        if not file_path.exists():
            # File was deleted; report as changed
            changed.append({"path": tracked_path, "status": "deleted"})
            continue

        try:
            current_mtime = get_file_mtime_ms(file_path)
        except OSError:
            # File became unreadable; treat as deleted
            changed.append({"path": tracked_path, "status": "deleted"})
            continue

        if current_mtime > old_mtime:
            # File was modified; read content and calculate changed lines
            changed_line_ranges = "1-EOF"
            try:
                new_content = file_path.read_text(encoding="utf-8")

                # Get old content if available
                old_content = session.contents.get(tracked_path, "")

                # Calculate which lines changed
                if old_content:
                    changed_line_ranges = calculate_changed_line_ranges(old_content, new_content)

                # Update cached content
                session.contents[tracked_path] = new_content
            except (OSError, UnicodeDecodeError):
                pass

            # Calculate seconds since file was modified
            seconds_ago = (current_mtime - old_mtime) / 1000

            changed.append(
                {
                    "path": tracked_path,
                    "status": "modified",
                    "changedLineRanges": changed_line_ranges,
                    "secondsAgo": int(seconds_ago) if seconds_ago >= 1 else f"{seconds_ago:.2f}",
                }
            )
            # Update the tracked mtime so we don't report this change again
            session.mtimes[tracked_path] = current_mtime

    return changed


def format_changed_files_section() -> str:
    """Get formatted [CHANGED_FILES] section and reset tracking.

    This function retrieves all changed files, formats them as a string section,
    and updates the cache so each change is only reported once.

    Returns:
        Formatted string with [CHANGED_FILES] section, or empty string if no changes.
    """
    changed_files = get_changed_files()
    if not changed_files:
        return ""

    response = "\n\n[CHANGED_FILES]"
    for changed in changed_files:
        response += f"\n- {changed['path']} ({changed['status']})"
        if "changedLineRanges" in changed:
            response += f": lines {changed['changedLineRanges']}"
        if "secondsAgo" in changed:
            response += f" ({changed['secondsAgo']}s ago)"

    return response
