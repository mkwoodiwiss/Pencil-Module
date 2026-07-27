"""High-level controller for the MF/UF Membrane Evaluation Unit.

The application entry point continues to re-export the public control classes
for compatibility with existing scripts and tests that import from
``system_control``.
"""

import json
import os

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


def main() -> None:
    """Start the MF/UF Membrane Evaluation Unit application."""
    # PencilModule is retained as the patchable entry-point symbol for older
    # integrations and tests. It is an alias of the preferred MEU class.
    meu = PencilModule()
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            defaults = json.load(fp)
    except Exception:
        defaults = {}
    app = HMI(meu, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
