"""Tests for config.py module.

Tests configuration loading from appsettings.json including
valid config, missing config, and error handling.
"""

import json
import sys
import unittest
from pathlib import Path

# Add parent directory to path for module imports
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from tests.test_utils import TempWorkspace


class TestConfigurationLoading(unittest.TestCase):
    """Tests for loading configuration files."""

    def test_load_instruction_file_names_from_valid_config(self) -> None:
        """Verify config is loaded from appsettings.json."""
        with TempWorkspace() as ws:
            from config import load_instruction_file_names

            config = {"instructionFileNames": ["CUSTOM.md", "OTHER.md"]}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            names = load_instruction_file_names(ws.path)

            self.assertEqual(names, ["CUSTOM.md", "OTHER.md"])

    def test_load_instruction_file_names_defaults_when_missing(self) -> None:
        """Verify default is used when config is missing."""
        with TempWorkspace() as ws:
            from config import load_instruction_file_names

            names = load_instruction_file_names(ws.path)

            self.assertEqual(names, ["AGENTS.md"])

    def test_load_instruction_file_names_defaults_on_invalid_json(self) -> None:
        """Verify default is used when config is invalid JSON."""
        with TempWorkspace() as ws:
            from config import load_instruction_file_names

            config_path = ws.path / "appsettings.json"
            config_path.write_text("not valid json {", encoding="utf-8")

            names = load_instruction_file_names(ws.path)

            self.assertEqual(names, ["AGENTS.md"])

    def test_load_instruction_file_names_defaults_on_missing_key(self) -> None:
        """Verify default when key is missing from valid JSON."""
        with TempWorkspace() as ws:
            from config import load_instruction_file_names

            config = {"otherSetting": "value"}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            names = load_instruction_file_names(ws.path)

            self.assertEqual(names, ["AGENTS.md"])


if __name__ == "__main__":
    unittest.main()
