"""File naming and CSV ownership for MEU automation runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
from pathlib import Path
import re
from typing import Any, Iterable, TextIO


def safe_name(value: str) -> str:
    """Return one filesystem-safe identifier, preserving the historical format."""
    text = (value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)


@dataclass
class AutomationLogFiles:
    """Own the data and settings files created for one automation run."""

    base_path: Path
    data_file: TextIO
    data_writer: Any

    @classmethod
    def open(
        cls,
        log_dir: str | Path,
        *,
        prefix: str,
        project: str,
        module_id: str,
        final_id: str,
        stamp: str,
        test_date: str,
        config: object,
        data_header: Iterable[str],
    ) -> "AutomationLogFiles":
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        filename = "_".join(
            safe_name(value)
            for value in (prefix, project, module_id, final_id, stamp)
        )
        base_path = directory / filename
        data_file = open(
            str(base_path) + "_data.csv",
            "w",
            newline="",
            encoding="utf-8",
        )
        data_writer = csv.writer(data_file)
        data_writer.writerow(data_header)
        data_file.flush()

        with open(
            str(base_path) + "_settings.csv",
            "w",
            newline="",
            encoding="utf-8",
        ) as settings_file:
            settings_writer = csv.writer(settings_file)
            settings_writer.writerow(["test_date", test_date])
            for key, value in asdict(config).items():
                settings_writer.writerow([key, value])

        return cls(base_path, data_file, data_writer)

    def close(self) -> None:
        """Close the data file safely; repeated calls are harmless."""
        if not self.data_file.closed:
            self.data_file.close()


__all__ = ["AutomationLogFiles", "safe_name"]
