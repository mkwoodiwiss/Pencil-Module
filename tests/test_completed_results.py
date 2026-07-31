"""Regression tests for exact completed-run result discovery."""

from pathlib import Path
import tempfile
import types
import unittest

from pencil.completed_results import (
    completed_result_files,
    files_from_log_session,
    latest_result_pair,
)


class TestCompletedResults(unittest.TestCase):
    def test_log_session_paths_are_preferred_over_newer_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned_data = root / "Test_A_data.csv"
            owned_settings = root / "Test_A_settings.csv"
            unrelated = root / "Test_B_data.csv"
            for path in (owned_data, owned_settings, unrelated):
                path.write_text(path.name, encoding="utf-8")

            system = types.SimpleNamespace(
                log_dir=directory,
                _log_files=types.SimpleNamespace(
                    data_path=owned_data,
                    settings_path=owned_settings,
                ),
            )

            self.assertEqual(
                completed_result_files(system),
                sorted((str(owned_data.resolve()), str(owned_settings.resolve()))),
            )

    def test_missing_owned_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "Test_A_data.csv"
            data.write_text("data", encoding="utf-8")
            system = types.SimpleNamespace(
                _log_files=types.SimpleNamespace(
                    data_path=data,
                    settings_path=root / "missing_settings.csv",
                )
            )

            self.assertEqual(files_from_log_session(system), [str(data.resolve())])

    def test_fallback_returns_only_matching_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_data = root / "Old_data.csv"
            new_data = root / "New_data.csv"
            new_settings = root / "New_settings.csv"
            old_data.write_text("old", encoding="utf-8")
            new_data.write_text("new", encoding="utf-8")
            new_settings.write_text("settings", encoding="utf-8")
            old_data.touch()
            new_data.touch()
            new_settings.touch()

            self.assertEqual(
                latest_result_pair(root),
                sorted((str(new_data.resolve()), str(new_settings.resolve()))),
            )

    def test_duplicate_session_paths_are_returned_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Run_data.csv"
            path.write_text("data", encoding="utf-8")
            system = types.SimpleNamespace(
                _log_files=types.SimpleNamespace(data_path=path, settings_path=path)
            )

            self.assertEqual(files_from_log_session(system), [str(path.resolve())])

    def test_empty_directory_returns_no_results(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(latest_result_pair(directory), [])


if __name__ == "__main__":
    unittest.main()
