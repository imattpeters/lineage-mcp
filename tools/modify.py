"""Unified file modification tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from file_watcher import format_changed_files_section
from path_utils import get_base_dir, get_file_mtime_ms, resolve_path
from session_state import session


OperationType = Literal["create", "overwrite", "append", "replace"]
OccurrenceMode = Literal["one", "all"]
OnErrorMode = Literal["abort", "continue"]

VALID_OPERATIONS: tuple[OperationType, ...] = ("create", "overwrite", "append", "replace")
VALID_OCCURRENCES: tuple[OccurrenceMode, ...] = ("one", "all")


class ModifyOperation(TypedDict, total=False):
    file_path: str
    operation: OperationType
    text: str
    match_text: str
    occurrence: OccurrenceMode


@dataclass
class OperationResult:
    success: bool
    message: str


def _tool_usage() -> str:
    return (
        "Call modify with operations=[{file_path, operation, text, ...}] and optional "
        "on_error='abort' or 'continue'. Replace operations also require match_text "
        "and may include occurrence='one' or 'all'."
    )


async def modify(
    operations: list[ModifyOperation],
    on_error: OnErrorMode = "abort",
) -> str:
    """Modify one or more text files by creating, overwriting, appending, or replacing exact text."""
    if not operations:
        return f"Error: No operations provided. {_tool_usage()}"

    if on_error not in ("abort", "continue"):
        return f"Error: invalid 'on_error'. {_tool_usage()}"

    results: list[str] = []

    for index, operation in enumerate(operations, 1):
        result = _apply_operation(index, operation)
        results.append(result.message)

        if not result.success and on_error == "abort":
            break

    output = "\n".join(results)
    changed_section = format_changed_files_section()
    if changed_section:
        output += f"\n\nEOF\n[Lineage Message]:{changed_section}"

    return output


def _operation_usage(operation_type: str | None = None) -> str:
    if operation_type == "replace":
        return (
            "Required keys for replace: file_path, operation='replace', match_text, text. "
            "Optional: occurrence='one' or 'all'."
        )

    if operation_type in ("create", "overwrite", "append"):
        return (
            f"Required keys for {operation_type}: file_path, operation='{operation_type}', text."
        )

    return (
        "Each operation must include file_path, operation, and text. "
        "Valid operation values: 'create', 'overwrite', 'append', 'replace'. "
        "Replace also requires match_text and optionally occurrence='one' or 'all'."
    )


def _apply_operation(index: int, operation: ModifyOperation) -> OperationResult:
    file_path = operation.get("file_path")
    operation_type = operation.get("operation")
    text = operation.get("text")
    match_text = operation.get("match_text")
    occurrence = operation.get("occurrence", "one")

    if not file_path:
        return OperationResult(
            False,
            f"Operation {index}: Error: missing 'file_path'. {_operation_usage(operation_type)}",
        )
    if operation_type not in VALID_OPERATIONS:
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: invalid 'operation'. {_operation_usage()}",
        )
    if text is None:
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: missing 'text'. {_operation_usage(operation_type)}",
        )

    if operation_type == "replace":
        if match_text is None:
            return OperationResult(
                False,
                f"Operation {index} ({file_path}): Error: missing 'match_text'. {_operation_usage('replace')}",
            )
        if occurrence not in VALID_OCCURRENCES:
            return OperationResult(
                False,
                f"Operation {index} ({file_path}): Error: invalid 'occurrence'. Allowed values: 'one' or 'all'. {_operation_usage('replace')}",
            )
    else:
        if match_text is not None:
            return OperationResult(
                False,
                f"Operation {index} ({file_path}): Error: 'match_text' is only valid for replace operations. {_operation_usage(operation_type)}",
            )
        if "occurrence" in operation:
            return OperationResult(
                False,
                f"Operation {index} ({file_path}): Error: 'occurrence' is only valid for replace operations. {_operation_usage(operation_type)}",
            )

    path_result = resolve_path(file_path)
    if not path_result.success:
        return OperationResult(False, f"Operation {index} ({file_path}): {path_result.error}")

    full_path = path_result.path

    if operation_type == "create":
        return _create_file(index, file_path, full_path, text)
    if operation_type == "overwrite":
        return _overwrite_file(index, file_path, full_path, text)
    if operation_type == "append":
        return _append_file(index, file_path, full_path, text)

    return _replace_in_file(index, file_path, full_path, text, match_text, occurrence)


def _create_file(index: int, file_path: str, full_path: Path, text: str) -> OperationResult:
    if full_path.exists():
        return OperationResult(False, f"Operation {index} ({file_path}): Error: File already exists")

    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(text, encoding="utf-8")
        _track_file(full_path, text)
        return OperationResult(True, f"Operation {index} ({file_path}): Successfully created file")
    except OSError as exc:
        return OperationResult(False, f"Operation {index} ({file_path}): Error writing file: {exc}")


def _overwrite_file(index: int, file_path: str, full_path: Path, text: str) -> OperationResult:
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(text, encoding="utf-8")
        _track_file(full_path, text)
        return OperationResult(True, f"Operation {index} ({file_path}): Successfully overwrote file")
    except OSError as exc:
        return OperationResult(False, f"Operation {index} ({file_path}): Error writing file: {exc}")


def _append_file(index: int, file_path: str, full_path: Path, text: str) -> OperationResult:
    if not full_path.exists():
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: File not found (base directory: {get_base_dir()})",
        )
    if not full_path.is_file():
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: Path is not a file (base directory: {get_base_dir()})",
        )

    try:
        existing = full_path.read_text(encoding="utf-8")
        new_content = existing + text
        full_path.write_text(new_content, encoding="utf-8")
        _track_file(full_path, new_content)
        return OperationResult(
            True,
            f"Operation {index} ({file_path}): Successfully appended {len(text)} character(s)",
        )
    except (OSError, UnicodeDecodeError) as exc:
        return OperationResult(False, f"Operation {index} ({file_path}): Error processing file: {exc}")


def _replace_in_file(
    index: int,
    file_path: str,
    full_path: Path,
    text: str,
    match_text: str,
    occurrence: OccurrenceMode,
) -> OperationResult:
    if not full_path.exists():
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: File not found (base directory: {get_base_dir()})",
        )
    if not full_path.is_file():
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: Path is not a file (base directory: {get_base_dir()})",
        )

    try:
        content = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return OperationResult(False, f"Operation {index} ({file_path}): Error reading file: {exc}")

    count = content.count(match_text)
    if count == 0:
        return OperationResult(False, f"Operation {index} ({file_path}): Error: String not found in file")

    if occurrence == "one" and count != 1:
        return OperationResult(
            False,
            f"Operation {index} ({file_path}): Error: String found {count} times. Use occurrence='all' or make the string more specific.",
        )

    if occurrence == "all":
        new_content = content.replace(match_text, text)
        replaced = count
    else:
        new_content = content.replace(match_text, text, 1)
        replaced = 1

    try:
        full_path.write_text(new_content, encoding="utf-8")
        _track_file(full_path, new_content)
        return OperationResult(
            True,
            f"Operation {index} ({file_path}): Successfully replaced {replaced} occurrence(s)",
        )
    except OSError as exc:
        return OperationResult(False, f"Operation {index} ({file_path}): Error writing file: {exc}")


def _track_file(full_path: Path, content: str) -> None:
    mtime = get_file_mtime_ms(full_path)
    session.track_file(str(full_path), mtime, content)
