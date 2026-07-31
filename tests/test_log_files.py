"""Tests for MEU automation log naming and file ownership."""

import csv
from dataclasses import dataclass
from pathlib import Path
import tempfile
import unittest

from pencil.log_files import AutomationLogFiles, safe_name


@dataclass
class _Config:
    cycle_count: int = 2
    project: str = "Project A"


class TestAutomationLogFiles(unittest.TestCase):
    def test_safe_name_preserves_historical_sanitizing(self):
        self.assertEqual(safe_name(" Project A / Test "), "Project_A_Test")
        self.assertEqual(safe_name(""), "unknown")
        self.assertEqual(safe_name("module-1.2"), "module-1.2")

    def test_open_creates_expected_data_and_settings_files(self):
        with tempfile.TemporaryDirectory() as directory:
            files = AutomationLogFiles.open(
                directory,
                prefix="Post Scrub",
                project="Project A",
                module_id="Module/1",
                final_id="Sample 2",
                stamp="20260731_113800",
                test_date="2026-07-31",
                config=_Config(),
                data_header=("timestamp", "step"),
            )
            try:
                self.assertEqual(
                    files.base_path.name,
                    "Post_Scrub_Project_A_Module_1_Sample_2_20260731_113800",
                )
                data_path = Path(str(files.base_path) + "_data.csv")
                settings_path = Path(str(files.base_path) + "_settings.csv")
                self.assertTrue(data_path.exists())
                self.assertTrue(settings_path.exists())

                with data_path.open(newline="", encoding="utf-8") as handle:
                    self.assertEqual(list(csv.reader(handle)), [["timestamp", "step"]])
                with settings_path.open(newline="", encoding="utf-8") as handle:
                    self.assertEqual(
                        list(csv.reader(handle)),
                        [
                            ["test_date", "2026-07-31"],
                            ["cycle_count", "2"],
                            ["project", "Project A"],
                        ],
                    )
            finally:
                files.close()

    def test_close_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            files = AutomationLogFiles.open(
                directory,
                prefix="Test",
                project="",
                module_id="",
                final_id="",
                stamp="stamp",
                test_date="date",
                config=_Config(),
                data_header=("step",),
            )
            files.close()
            files.close()
            self.assertTrue(files.data_file.closed)


if __name__ == "__main__":
    unittest.main()
