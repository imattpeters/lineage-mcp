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


class TestClientOverrides(unittest.TestCase):
    """Tests for per-client configuration overrides."""

    def test_load_client_overrides_from_valid_config(self) -> None:
        """Verify clientOverrides are loaded from appsettings.json."""
        with TempWorkspace() as ws:
            from config import load_client_overrides

            config = {
                "clientOverrides": {
                    "OpenCode": {"readCharLimit": 50000},
                    "Cursor": {"readCharLimit": 15000},
                }
            }
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            overrides = load_client_overrides(ws.path)

            self.assertEqual(overrides["OpenCode"]["readCharLimit"], 50000)
            self.assertEqual(overrides["Cursor"]["readCharLimit"], 15000)

    def test_load_client_overrides_returns_empty_when_missing(self) -> None:
        """Verify empty dict returned when no clientOverrides key."""
        with TempWorkspace() as ws:
            from config import load_client_overrides

            config = {"readCharLimit": 7000}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            overrides = load_client_overrides(ws.path)

            self.assertEqual(overrides, {})

    def test_load_client_overrides_returns_empty_on_no_file(self) -> None:
        """Verify empty dict returned when no config file."""
        with TempWorkspace() as ws:
            from config import load_client_overrides

            overrides = load_client_overrides(ws.path)

            self.assertEqual(overrides, {})

    def test_load_client_overrides_returns_empty_on_invalid_json(self) -> None:
        """Verify empty dict on invalid JSON."""
        with TempWorkspace() as ws:
            from config import load_client_overrides

            config_path = ws.path / "appsettings.json"
            config_path.write_text("not valid json", encoding="utf-8")

            overrides = load_client_overrides(ws.path)

            self.assertEqual(overrides, {})

    def test_load_client_overrides_returns_empty_on_non_dict(self) -> None:
        """Verify empty dict when clientOverrides is not a dict."""
        with TempWorkspace() as ws:
            from config import load_client_overrides

            config = {"clientOverrides": "not a dict"}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            overrides = load_client_overrides(ws.path)

            self.assertEqual(overrides, {})


class TestGetReadCharLimit(unittest.TestCase):
    """Tests for get_read_char_limit resolution logic."""

    def test_returns_global_default_when_no_client_name(self) -> None:
        """No client name returns global READ_CHAR_LIMIT."""
        import config

        result = config.get_read_char_limit(None)

        self.assertEqual(result, config.READ_CHAR_LIMIT)

    def test_returns_global_default_when_client_not_in_overrides(self) -> None:
        """Unknown client name falls back to global limit."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": 50000}}
        try:
            result = config.get_read_char_limit("UnknownClient")
            self.assertEqual(result, config.READ_CHAR_LIMIT)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_returns_override_when_client_matches(self) -> None:
        """Client name in overrides returns specific limit."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": 50000}}
        try:
            result = config.get_read_char_limit("OpenCode")
            self.assertEqual(result, 50000)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_falls_back_when_override_missing_readcharlimit(self) -> None:
        """Client override without readCharLimit falls back to global."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"otherSetting": True}}
        try:
            result = config.get_read_char_limit("OpenCode")
            self.assertEqual(result, config.READ_CHAR_LIMIT)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_falls_back_when_override_has_invalid_value(self) -> None:
        """Client override with non-int readCharLimit falls back to global."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": "not_an_int"}}
        try:
            result = config.get_read_char_limit("OpenCode")
            self.assertEqual(result, config.READ_CHAR_LIMIT)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_falls_back_when_override_value_is_zero(self) -> None:
        """Client override with readCharLimit=0 falls back to global."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": 0}}
        try:
            result = config.get_read_char_limit("OpenCode")
            self.assertEqual(result, config.READ_CHAR_LIMIT)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_falls_back_when_override_value_is_negative(self) -> None:
        """Client override with negative readCharLimit falls back to global."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": -100}}
        try:
            result = config.get_read_char_limit("OpenCode")
            self.assertEqual(result, config.READ_CHAR_LIMIT)
        finally:
            config.CLIENT_OVERRIDES = old_overrides

    def test_empty_string_client_name_returns_global(self) -> None:
        """Empty string client name returns global default."""
        import config

        result = config.get_read_char_limit("")

        self.assertEqual(result, config.READ_CHAR_LIMIT)

    def test_case_insensitive_client_name_lookup(self) -> None:
        """Client name lookup is case-insensitive."""
        import config

        old_overrides = config.CLIENT_OVERRIDES
        config.CLIENT_OVERRIDES = {"OpenCode": {"readCharLimit": 50000}}
        try:
            self.assertEqual(config.get_read_char_limit("opencode"), 50000)
            self.assertEqual(config.get_read_char_limit("OPENCODE"), 50000)
            self.assertEqual(config.get_read_char_limit("OpenCode"), 50000)
            self.assertEqual(config.get_read_char_limit("openCode"), 50000)
        finally:
            config.CLIENT_OVERRIDES = old_overrides


class TestDebugClientInfo(unittest.TestCase):
    """Tests for the debugClientInfo setting."""

    def test_load_debug_client_info_default(self) -> None:
        """Default is False when no config file."""
        with TempWorkspace() as ws:
            from config import load_debug_client_info

            result = load_debug_client_info(ws.path)

            self.assertFalse(result)

    def test_load_debug_client_info_true(self) -> None:
        """Returns True when set in config."""
        with TempWorkspace() as ws:
            from config import load_debug_client_info

            config = {"debugClientInfo": True}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = load_debug_client_info(ws.path)

            self.assertTrue(result)

    def test_load_debug_client_info_false(self) -> None:
        """Returns False when explicitly set to false."""
        with TempWorkspace() as ws:
            from config import load_debug_client_info

            config = {"debugClientInfo": False}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = load_debug_client_info(ws.path)

            self.assertFalse(result)

    def test_load_debug_client_info_ignores_non_bool(self) -> None:
        """Returns default when value is not a boolean."""
        with TempWorkspace() as ws:
            from config import load_debug_client_info

            config = {"debugClientInfo": "yes"}
            config_path = ws.path / "appsettings.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = load_debug_client_info(ws.path)

            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
