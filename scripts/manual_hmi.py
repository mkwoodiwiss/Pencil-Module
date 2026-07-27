"""Run the MEU HMI using simulated hardware for manual testing.

This helper is useful during development when the real MF/UF Membrane
Evaluation Unit hardware is unavailable.
"""

import json
import os

from tests.test_interfaces import SimulatedMEU
from system_control import HMI


def main() -> None:
    """Launch the MEU HMI with simulated hardware attached."""
    meu = SimulatedMEU()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            defaults = json.load(fp)
    except Exception:
        defaults = {}
    app = HMI(meu, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
