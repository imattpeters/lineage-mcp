"""Instruction file discovery for the MCP file server.

Handles discovery and inclusion of AGENTS.md, CLAUDE.md, and other
instruction files from parent directories.
"""

from pathlib import Path
from typing import List

from config import INSTRUCTION_FILE_NAMES
from path_utils import get_base_dir
from session_state import session


def find_instruction_files_in_parents(target_path: Path) -> List[tuple[Path, Path]]:
    """Find instruction files walking up from target path to BASE_DIR.

    Walks UP the directory tree from the parent of target_path until BASE_DIR,
    looking for instruction files in each folder. For each folder, checks for
    instruction files in priority order (INSTRUCTION_FILE_NAMES) and includes
    only the first one found per folder.

    Normally does NOT include instruction files at BASE_DIR, since the harness
    (VS Code, OpenCode) loads them on first boot. However, after context
    compaction (detected by session clear count >= 2), base directory instruction
    files ARE included so the LLM can recover that context.

    Args:
        target_path: Path to the file being read (absolute).

    Returns:
        List of (folder_path, file_path) tuples, sorted closest to BASE_DIR first.
        Each folder appears at most once. Empty list if none found.
    """
    found: List[tuple[Path, Path]] = []
    base_dir = get_base_dir()

    # Start from parent of file (or the path itself if it's a directory)
    current = target_path.parent if target_path.is_file() else target_path

    while True:
        # Stop if we've reached BASE_DIR
        if current.resolve() == base_dir.resolve():
            break

        # Check for instruction files in priority order
        for file_name in INSTRUCTION_FILE_NAMES:
            instruction_file = current / file_name
            if instruction_file.is_file():
                # Found one - add tuple and stop checking this folder
                found.append((current, instruction_file))
                break

        # Move up one directory
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    # After compaction, also include base directory instruction files
    # so the LLM can recover context lost during summarisation
    if session.should_include_base_instruction_files():
        for file_name in INSTRUCTION_FILE_NAMES:
            instruction_file = base_dir / file_name
            if instruction_file.is_file():
                found.append((base_dir, instruction_file))
                break

    return found


def include_instruction_file_content(instruction_files: List[tuple[Path, Path]]) -> str:
    """Generate response sections for instruction files.

    Reads instruction files, checks if folder has already been provided in session,
    updates cache, and returns formatted response sections.

    Args:
        instruction_files: List of (folder_path, file_path) tuples.

    Returns:
        Formatted string with [INSTRUCTION FILE] sections, or empty string if none.
    """
    output: List[str] = []

    for folder_path, file_path in instruction_files:
        if not file_path.is_file():
            continue

        folder_str = str(folder_path)

        # Check if we've already provided an instruction file for this folder
        if session.is_folder_provided(folder_str):
            # Already provided - skip (only new_session=True resets this)
            continue

        # New folder; include its instruction file
        try:
            content = file_path.read_text(encoding="utf-8")

            # Format the response section
            output.append(f"\n[Appending {file_path}]")
            output.append(content)

            # Mark folder as provided
            session.mark_folder_provided(folder_str)

        except (OSError, UnicodeDecodeError):
            # File is corrupted or unreadable
            output.append(f"\n[Appending {file_path}]")
            output.append("[File Corrupted]")
            session.mark_folder_provided(folder_str)

    return "".join(output)


def mark_instruction_folder_if_applicable(target_file: Path) -> None:
    """Mark an instruction file's folder as provided if applicable.

    Call this after reading/writing/editing an instruction file to prevent
    it from being re-appended on subsequent reads.

    Args:
        target_file: Path to the file being operated on.
    """
    if target_file.name in INSTRUCTION_FILE_NAMES:
        session.mark_folder_provided(str(target_file.parent))
