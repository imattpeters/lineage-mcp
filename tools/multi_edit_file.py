"""Multi-edit file tool - batch string replacements across multiple files."""

from pathlib import Path
from typing import Any

from file_watcher import format_changed_files_section
from path_utils import get_file_mtime_ms, resolve_path
from session_state import session


async def multi_edit_file(
    edits: list[dict[str, Any]],
    new_session: bool = False,
) -> str:
    """Edit multiple files by replacing exact string matches in a single batch.

    Each edit in the list specifies a file, the old string to find, and the new
    string to replace it with. All edits are applied sequentially. If one edit
    fails, the error is reported but remaining edits still proceed.

    Args:
        edits: List of edit operations. Each dict must contain:
            - file_path (str): Path to the file relative to the base directory
            - old_string (str): Exact text to find and replace
            - new_string (str): Text to replace old_string with
            - replace_all (bool, optional): If True, replace all occurrences.
              Defaults to False.
        new_session: If True, clears all server caches before operation.

    Returns:
        Combined results for all edits, with per-edit success/error messages.
    """
    # Handle new_session - clear all caches
    if new_session:
        session.try_new_session()

    if not edits:
        return "Error: No edits provided"

    results: list[str] = []

    for i, edit in enumerate(edits, 1):
        # Validate required fields
        file_path = edit.get("file_path")
        old_string = edit.get("old_string")
        new_string = edit.get("new_string")
        replace_all = edit.get("replace_all", False)

        if not file_path:
            results.append(f"Edit {i}: Error: missing 'file_path'")
            continue
        if old_string is None:
            results.append(f"Edit {i}: Error: missing 'old_string'")
            continue
        if new_string is None:
            results.append(f"Edit {i}: Error: missing 'new_string'")
            continue

        # Resolve and validate path
        path_result = resolve_path(file_path)
        if not path_result.success:
            results.append(f"Edit {i} ({file_path}): {path_result.error}")
            continue

        full_path = path_result.path
        if not full_path.exists():
            results.append(f"Edit {i} ({file_path}): Error: File not found")
            continue
        if not full_path.is_file():
            results.append(f"Edit {i} ({file_path}): Error: Path is not a file")
            continue

        # Read file content
        try:
            content = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            results.append(f"Edit {i} ({file_path}): Error reading file: {e}")
            continue

        # Count occurrences
        count = content.count(old_string)
        if count == 0:
            results.append(f"Edit {i} ({file_path}): Error: String not found in file")
            continue

        if not replace_all and count > 1:
            results.append(
                f"Edit {i} ({file_path}): Error: String found {count} times. "
                "Use replace_all=True to replace all, or make the string more specific."
            )
            continue

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)

        try:
            full_path.write_text(new_content, encoding="utf-8")

            # Track file for change detection
            file_path_str = str(full_path)
            mtime = get_file_mtime_ms(full_path)
            session.track_file(file_path_str, mtime, new_content)

            results.append(
                f"Edit {i} ({file_path}): Successfully replaced {count} occurrence(s)"
            )
        except OSError as e:
            results.append(f"Edit {i} ({file_path}): Error writing file: {e}")

    output = "\n".join(results)

    # Append changed files section
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\n{changed_section}"

    return output
