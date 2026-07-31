"""Discover the exact result files produced by a completed MEU run."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def _existing_paths(paths: Iterable[object]) -> list[str]:
    """Return existing file paths as sorted absolute strings."""
    existing: list[str] = []
    for value in paths:
        if value is None:
            continue
        try:
            path = Path(value).resolve()
        except (TypeError, ValueError, OSError):
            continue
        if path.is_file():
            existing.append(str(path))
    return sorted(dict.fromkeys(existing))


def files_from_log_session(test_system: object) -> list[str]:
    """Return the files owned by the automation's active log session."""
    session = getattr(test_system, "_log_files", None)
    if session is None:
        return []
    return _existing_paths(
        (
            getattr(session, "data_path", None),
            getattr(session, "settings_path", None),
        )
    )


def latest_result_pair(log_dir: os.PathLike[str] | str) -> list[str]:
    """Compatibility fallback returning the newest matching data/settings pair."""
    directory = Path(log_dir)
    try:
        candidates = [
            path
            for path in directory.iterdir()
            if path.is_file()
            and (path.name.endswith("_data.csv") or path.name.endswith("_settings.csv"))
        ]
    except OSError:
        return []
    if not candidates:
        return []

    newest = max(candidates, key=lambda path: path.stat().st_mtime)
    stem = newest.name
    for suffix in ("_data.csv", "_settings.csv"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return _existing_paths(
        path for path in candidates if path.name in {f"{stem}_data.csv", f"{stem}_settings.csv"}
    )


def completed_result_files(test_system: object | None, default_log_dir: str = "logs") -> list[str]:
    """Return exact run-owned result files, then fall back to legacy discovery."""
    if test_system is not None:
        owned = files_from_log_session(test_system)
        if owned:
            return owned
    log_dir = getattr(test_system, "log_dir", default_log_dir)
    return latest_result_pair(log_dir)


class CompletedResultsMixin:
    """Provide exact completed-run discovery to the touchscreen runtime."""

    def _latest_saved_files(self) -> list[str]:
        return completed_result_files(getattr(self, "test_system", None))


__all__ = [
    "CompletedResultsMixin",
    "completed_result_files",
    "files_from_log_session",
    "latest_result_pair",
]
