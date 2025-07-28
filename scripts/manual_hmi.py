"""Run the GUI using simulated hardware for manual testing.

This helper script is useful during development when the real
hardware is not available. It imports the simulated interfaces from
the test suite and instantiates the normal :class:`HMI` so the user
can interact with the GUI.
"""

import json
import os

from tests.test_interfaces import SimulatedPencilModule
from system_control import HMI


def main() -> None:
    """Launch the HMI with simulated hardware attached."""
    module = SimulatedPencilModule()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            defaults = json.load(fp)
    except Exception:
        defaults = {}
    app = HMI(module, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
