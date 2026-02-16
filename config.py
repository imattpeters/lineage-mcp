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

# Default settings for multi_read and multi_edit tools
DEFAULT_ENABLE_MULTI_READ: bool = True
DEFAULT_ENABLE_MULTI_EDIT: bool = True

# Default character limit for pagination
DEFAULT_READ_CHAR_LIMIT: int = 50000

# Default debug client info setting
DEFAULT_DEBUG_CLIENT_INFO: bool = False

# Default allow full paths setting (restrict to base dir)
DEFAULT_ALLOW_FULL_PATHS: bool = False

# Default interrupt message appended when user clicks Interrupt in system tray
DEFAULT_INTERRUPT_MESSAGE: str = """\n
This is not the result you are looking for.
The MCP TOOLS has been disabled by the user. 
Please read the message below and follow the instructions to re-enable the tools.

⚠️⚠️⚠️ CRITICAL INTERRUPT ⚠️⚠️⚠️
HALT ALL OPERATIONS IMMEDIATELY
════════════════════════════════════════
YOU MUST STOP EVERYTHING RIGHT NOW
- Cancel all pending file operations
- Do not execute any more code
- Do not continue with any tasks
- Do not complete any work in progress

THE LINAGE MCP TOOL WILL NOT WORK UNTIL YOU TALK TO THE USER!

USE ask_user() IMMEDIATELY
WAIT FOR USER INPUT BEFORE PROCEEDING

DO NOT RESUME UNTIL USER RESPONDS
════════════════════════════════════════"""


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


def load_enable_multi_read(config_dir: Path | None = None) -> bool:
    """Load the enableMultiRead setting from appsettings.json.

    Controls whether the multi_read tool is registered and available.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Boolean indicating if multi_read tool should be enabled. Defaults to True.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("enableMultiRead")
                if isinstance(value, bool):
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_ENABLE_MULTI_READ


def load_enable_multi_edit(config_dir: Path | None = None) -> bool:
    """Load the enableMultiEdit setting from appsettings.json.

    Controls whether the multi_edit tool is registered and available.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Boolean indicating if multi_edit tool should be enabled. Defaults to True.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("enableMultiEdit")
                if isinstance(value, bool):
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_ENABLE_MULTI_EDIT


def load_read_char_limit(config_dir: Path | None = None) -> int:
    """Load read character limit from appsettings.json.

    Controls the maximum characters returned per page when reading files.
    Files exceeding this limit are automatically paginated with line-aware
    truncation.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Character limit as integer. Defaults to 50000.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("readCharLimit")
                if isinstance(value, int) and value > 0:
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_READ_CHAR_LIMIT


def load_debug_client_info(config_dir: Path | None = None) -> bool:
    """Load the debugClientInfo setting from appsettings.json.

    When enabled, the detected MCP client name and effective readCharLimit
    are prepended to read() responses for debugging purposes.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Boolean indicating if debug client info should be shown. Defaults to False.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("debugClientInfo")
                if isinstance(value, bool):
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_DEBUG_CLIENT_INFO


def load_allow_full_paths(config_dir: Path | None = None) -> bool:
    """Load the allowFullPaths setting from appsettings.json.

    When enabled, file operations are not restricted to the base directory.
    Any absolute path on the system can be accessed. Use with caution.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Boolean indicating if full paths are allowed. Defaults to False.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("allowFullPaths")
                if isinstance(value, bool):
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_ALLOW_FULL_PATHS


def load_client_overrides(config_dir: Path | None = None) -> dict:
    """Load per-client configuration overrides from appsettings.json.

    Reads the 'clientOverrides' object from appsettings.json. Each key is a
    client name (matching the MCP clientInfo.name sent during initialization),
    and the value is a dict of config overrides for that client.

    Example config:
        {
            "clientOverrides": {
                "OpenCode": { "readCharLimit": 50000 },
                "Cursor": { "readCharLimit": 15000 }
            }
        }

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        Dict mapping client names to their config overrides.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                overrides = config.get("clientOverrides")
                if isinstance(overrides, dict):
                    return overrides
    except (OSError, json.JSONDecodeError):
        pass

    return {}


def get_read_char_limit(client_name: str | None = None) -> int:
    """Get the effective readCharLimit for a given client.

    Checks clientOverrides first for a client-specific value (case-insensitive),
    then falls back to the global READ_CHAR_LIMIT.

    Args:
        client_name: The MCP client name from clientInfo.name
                     (e.g. "OpenCode", "claude-desktop").
                     If None, returns the global default.

    Returns:
        Character limit as integer.
    """
    if client_name:
        # Case-insensitive lookup: build a lower-case mapping
        client_name_lower = client_name.lower()
        for key, override in CLIENT_OVERRIDES.items():
            if key.lower() == client_name_lower and isinstance(override, dict):
                value = override.get("readCharLimit")
                if isinstance(value, int) and value > 0:
                    return value

    return READ_CHAR_LIMIT


def load_interrupt_message(config_dir: Path | None = None) -> str:
    """Load the interrupt message from appsettings.json.

    This message is appended to tool results when the user clicks
    "Interrupt" in the system tray.

    Args:
        config_dir: Directory containing appsettings.json. If None, uses script directory.

    Returns:
        The interrupt message string.
    """
    if config_dir is None:
        config_dir = Path(__file__).parent

    config_path = config_dir / "appsettings.json"

    try:
        if config_path.is_file():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                value = config.get("interruptMessage")
                if isinstance(value, str) and len(value) > 0:
                    return value
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_INTERRUPT_MESSAGE


# Singleton: Load instruction file names at module import
INSTRUCTION_FILE_NAMES: List[str] = load_instruction_file_names()
ENABLE_MULTI_READ: bool = load_enable_multi_read()
ENABLE_MULTI_EDIT: bool = load_enable_multi_edit()
READ_CHAR_LIMIT: int = load_read_char_limit()
CLIENT_OVERRIDES: dict = load_client_overrides()
DEBUG_CLIENT_INFO: bool = load_debug_client_info()
ALLOW_FULL_PATHS: bool = load_allow_full_paths()
INTERRUPT_MESSAGE: str = load_interrupt_message()
