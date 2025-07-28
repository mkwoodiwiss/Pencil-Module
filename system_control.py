"""High level controller for the Pencil Module."""

import json
import os

from pencil import (
    FiltrationConfig,
    FiltrationTestSystem,
    HMI,
    PencilModule,
)


def main() -> None:
    """Entry point when running the module directly."""
    module = PencilModule()
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            defaults = json.load(fp)
    except Exception:
        defaults = {}
    app = HMI(module, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
