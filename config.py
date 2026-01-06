"""Configuration management for the MCP file server.

Handles loading settings from appsettings.json with sensible defaults.
"""

import json
from pathlib import Path
from typing import List


# Default instruction file names to look for (in priority order)
DEFAULT_INSTRUCTION_FILE_NAMES = ["AGENTS.md"]


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


# Singleton: Load instruction file names at module import
INSTRUCTION_FILE_NAMES: List[str] = load_instruction_file_names()
