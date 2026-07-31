"""Production entry point for the MF/UF Membrane Evaluation Unit.

Public control classes remain re-exported for compatibility with existing Pi
scripts and tests. Startup policy is intentionally kept small and explicit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pencil import (
    BenchmarkConfig,
    BenchmarkTestSystem,
    CleanConfig,
    CleanTestSystem,
    EmulatedMEU,
    FiltrationConfig,
    FiltrationTestSystem,
    HMI,
    MEU,
    PencilModule,
)
from pencil.config_loader import load_defaults


__all__ = [
    "MEU",
    "PencilModule",
    "EmulatedMEU",
    "FiltrationConfig",
    "FiltrationTestSystem",
    "CleanConfig",
    "CleanTestSystem",
    "BenchmarkConfig",
    "BenchmarkTestSystem",
    "HMI",
    "main",
]


APPLICATION_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = APPLICATION_ROOT / "config.json"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _load_defaults(config_path: str | Path) -> dict[str, Any]:
    """Compatibility wrapper around the package configuration loader."""
    return load_defaults(config_path)


def _emulation_requested(environment: dict[str, str] | None = None) -> bool:
    """Return True only for an explicit MEU_EMULATE_RPI opt-in value."""
    source = os.environ if environment is None else environment
    return source.get("MEU_EMULATE_RPI", "").strip().lower() in _TRUE_VALUES


def _create_module():
    """Create deterministic emulation on request, otherwise production hardware."""
    if _emulation_requested():
        return EmulatedMEU()
    return PencilModule()


def main() -> None:
    """Create the hardware backend and run the production Tkinter HMI."""
    module = _create_module()
    app = HMI(module, fullscreen=True, defaults=_load_defaults(CONFIG_PATH))
    app.mainloop()


if __name__ == "__main__":
    main()
