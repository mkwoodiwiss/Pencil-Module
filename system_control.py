"""High-level controller for the MF/UF Membrane Evaluation Unit.

The application entry point continues to re-export the public control classes
for compatibility with existing scripts and tests that import from
``system_control``.
"""

import json
import os
from typing import Any

from pencil import (
    BenchmarkConfig,
    BenchmarkTestSystem,
    CleanConfig,
    CleanTestSystem,
    FiltrationConfig,
    FiltrationTestSystem,
    HMI,
    MEU,
    PencilModule,
)


__all__ = [
    "MEU",
    "PencilModule",
    "FiltrationConfig",
    "FiltrationTestSystem",
    "CleanConfig",
    "CleanTestSystem",
    "BenchmarkConfig",
    "BenchmarkTestSystem",
    "HMI",
    "main",
]


def _load_defaults(config_path: str) -> dict[str, Any]:
    """Load HMI defaults from JSON while preserving a missing-file fallback.

    A missing configuration file is treated as an intentional request to use
    built-in defaults. Existing but malformed or unreadable files raise a clear
    startup error so configuration problems are not silently ignored.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            defaults = json.load(config_file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON in MEU configuration file: {config_path}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Unable to read MEU configuration file: {config_path}"
        ) from exc

    if not isinstance(defaults, dict):
        raise RuntimeError(
            f"MEU configuration must contain a JSON object: {config_path}"
        )
    return defaults


def main() -> None:
    """Start the MF/UF Membrane Evaluation Unit application."""
    # PencilModule is retained as the patchable entry-point symbol for older
    # integrations and tests. It is an alias of the preferred MEU class.
    meu = PencilModule()
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    defaults = _load_defaults(config_path)
    app = HMI(meu, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
