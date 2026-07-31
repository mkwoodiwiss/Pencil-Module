"""Production entry point for the MF/UF Membrane Evaluation Unit.

This file should remain deliberately boring.  Its job is only to:

1. Load the optional operator defaults from ``config.json``.
2. Select either the real Raspberry Pi hardware or the deterministic emulator.
3. Construct the final HMI and enter Tkinter's main loop.

Do not move process logic, hardware mappings, or HMI layout code back into this
module.  Keeping startup thin makes it possible to import and test the package
without accidentally opening serial ports, energizing relays, or creating a Tk
window.

Several classes are re-exported from here because older Pi scripts and tests
historically imported them from ``system_control``.  Those exports are part of
the compatibility surface even though their implementations now live in the
``pencil`` package.
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


# Keep this list synchronized with the compatibility imports above.  Removing a
# name can break external scripts even when the production application itself
# still starts correctly.
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


# Resolve configuration relative to this file, not the current working
# directory.  The MEU is frequently launched by desktop shortcuts, systemd, or
# a remote shell whose working directory is not the repository root.
APPLICATION_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = APPLICATION_ROOT / "config.json"

# Emulation must be an explicit opt-in.  Unknown values intentionally fall back
# to real hardware so a misspelled environment value cannot silently change the
# production startup path.
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _load_defaults(config_path: str | Path) -> dict[str, Any]:
    """Load optional HMI defaults while preserving the historical helper name."""
    return load_defaults(config_path)


def _emulation_requested(environment: dict[str, str] | None = None) -> bool:
    """Return ``True`` only for an explicit ``MEU_EMULATE_RPI`` opt-in value.

    ``environment`` is injectable for tests.  Production callers leave it as
    ``None`` so the process environment is used.
    """
    source = os.environ if environment is None else environment
    return source.get("MEU_EMULATE_RPI", "").strip().lower() in _TRUE_VALUES


def _create_module():
    """Create the selected hardware backend without changing the public API."""
    if _emulation_requested():
        # The emulator mirrors the methods consumed by automation and the HMI,
        # but it never opens Pi devices or energizes physical outputs.
        return EmulatedMEU()

    # ``PencilModule`` is the historical production class name.  It remains an
    # alias for the current MEU runtime implementation for compatibility.
    return PencilModule()


def main() -> None:
    """Create the backend, construct the fullscreen HMI, and block in Tk."""
    module = _create_module()
    app = HMI(module, fullscreen=True, defaults=_load_defaults(CONFIG_PATH))
    app.mainloop()


if __name__ == "__main__":
    main()
