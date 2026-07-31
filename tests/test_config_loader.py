"""Tests for MEU JSON configuration loading."""

import json
import tempfile
import unittest
from pathlib import Path

from pencil.config_loader import ConfigurationError, load_defaults


class TestConfigurationLoader(unittest.TestCase):
    def test_missing_file_uses_built_in_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            self.assertEqual(load_defaults(missing), {})

    def test_valid_object_is_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps({"cycle_count": 3, "project": "demo"}),
                encoding="utf-8",
            )

            self.assertEqual(
                load_defaults(config_path),
                {"cycle_count": 3, "project": "demo"},
            )

    def test_malformed_json_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text("{bad json", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "Invalid JSON"):
                load_defaults(config_path)

    def test_non_object_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text("[]", encoding="utf-8")

            with self.assertRaisesRegex(ConfigurationError, "JSON object"):
                load_defaults(config_path)


if __name__ == "__main__":
    unittest.main()
