"""Instruction file discovery for the MCP file server.

Handles discovery and inclusion of AGENTS.md, CLAUDE.md, and other
instruction files from parent directories.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from config import INSTRUCTION_FILE_NAMES
from path_utils import get_base_dir
from session_state import session


@dataclass(frozen=True)
class InstructionFileRenderItem:
    """A single instruction file and how it should be surfaced in a read."""

    folder_path: Path
    file_path: Path
    include_content: bool


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


def plan_instruction_file_output(
    instruction_files: List[tuple[Path, Path]],
) -> List[InstructionFileRenderItem]:
    """Decide whether each discovered instruction file is content or path-only.

    A folder whose instruction content has already been appended in this session
    is still surfaced, but only by path so the agent knows the file exists.
    """
    render_items: List[InstructionFileRenderItem] = []

    for folder_path, file_path in instruction_files:
        if not file_path.is_file():
            continue

        render_items.append(
            InstructionFileRenderItem(
                folder_path=folder_path,
                file_path=file_path,
                include_content=not session.has_appended_instruction_content(
                    str(folder_path)
                ),
            )
        )

    return render_items


def render_instruction_file_output(
    render_items: List[InstructionFileRenderItem],
) -> str:
    """Render instruction file output for a read response."""
    output: List[str] = []
    available_paths: List[str] = []

    for item in render_items:
        if item.include_content:
            try:
                content = item.file_path.read_text(encoding="utf-8")
                output.append(f"\n[Appending {item.file_path}]")
                output.append(content)
            except (OSError, UnicodeDecodeError):
                output.append(f"\n[Appending {item.file_path}]")
                output.append("[File Corrupted]")

            session.mark_instruction_content_appended(str(item.folder_path))
            continue

        available_paths.append(str(item.file_path))

    if available_paths:
        if len(available_paths) == 1:
            output.append("\n[Instruction file available]")
        else:
            output.append("\n[Instruction files available]")

        for file_path in available_paths:
            output.append(f"\n- {file_path}")

    return "".join(output)


def include_instruction_file_content(instruction_files: List[tuple[Path, Path]]) -> str:
    """Generate response sections for instruction files."""
    render_items = plan_instruction_file_output(instruction_files)
    return render_instruction_file_output(render_items)


def mark_instruction_content_appended_if_applicable(target_file: Path) -> None:
    """Mark an instruction file's folder as appended if applicable.

    Call this after reading/writing/editing an instruction file to prevent
    it from being re-appended on subsequent reads while still surfacing
    its path to the agent.

    Args:
        target_file: Path to the file being operated on.
    """
    if target_file.name in INSTRUCTION_FILE_NAMES:
        session.mark_instruction_content_appended(str(target_file.parent))
