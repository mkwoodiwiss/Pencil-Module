"""High-level controller for the MF/UF Membrane Evaluation Unit."""

import json
import os

from pencil import HMI, MEU


def main() -> None:
    """Start the MF/UF Membrane Evaluation Unit application."""
    meu = MEU()
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
