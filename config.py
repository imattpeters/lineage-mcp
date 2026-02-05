"""Configuration management for the MCP file server.

Handles loading settings from appsettings.json with sensible defaults.
"""

import json
from pathlib import Path
from typing import List


# Default instruction file names to look for (in priority order)
DEFAULT_INSTRUCTION_FILE_NAMES = ["AGENTS.md"]

# Default cooldown before a new new_session=True clear is honoured (seconds)
DEFAULT_NEW_SESSION_COOLDOWN_SECONDS: float = 30.0


def load_instruction_file_names(config_dir: Path | None = None) -> List[str]:
    """Load instruction file names from appsettings.json.

    Reads the 'instructionFileNames' array from appsettings.json if it exists.
    Falls back to DEFAULT_INSTRUCTION_FILE_NAMES if file doesn't exist or
    property is missing.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        List of instruction file names in priority order.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                file_names = config.get("instructionFileNames")
                if isinstance(file_names, list) and len(file_names) > 0:
                    return file_names
    except (OSError, json.JSONDecodeError):
        # Config file corrupted or unreadable - use defaults
        pass

    return DEFAULT_INSTRUCTION_FILE_NAMES.copy()


def load_new_session_cooldown_seconds(config_dir: Path | None = None) -> float:
    """Load the new_session cooldown from appsettings.json.

    When new_session=True is received, caches are only cleared if at least
    this many seconds have elapsed since the last clear. This prevents
    redundant cache clears during the initial burst of AI tool calls.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Cooldown in seconds (float). Defaults to 30.0.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("newSessionCooldownSeconds")
                if isinstance(value, (int, float)) and value >= 0:
                    return float(value)
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_NEW_SESSION_COOLDOWN_SECONDS


# Singleton: Load instruction file names at module import
INSTRUCTION_FILE_NAMES: List[str] = load_instruction_file_names()
