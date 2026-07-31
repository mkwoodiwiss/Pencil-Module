"""Configuration loading for the MEU application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigurationError(RuntimeError):
    """Raised when an existing MEU configuration cannot be used."""


def load_defaults(config_path: str | Path) -> dict[str, Any]:
    """Load HMI defaults while treating a missing file as built-in defaults."""
    path = Path(config_path)
    try:
        with path.open("r", encoding="utf-8") as config_file:
            defaults = json.load(config_file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"Invalid JSON in MEU configuration file: {path}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            f"Unable to read MEU configuration file: {path}"
        ) from exc

    if not isinstance(defaults, dict):
        raise ConfigurationError(
            f"MEU configuration must contain a JSON object: {path}"
        )
    return defaults


__all__ = ["ConfigurationError", "load_defaults"]
