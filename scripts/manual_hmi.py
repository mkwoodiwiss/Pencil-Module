"""Run the MEU HMI using simulated hardware for manual testing.

This helper is useful during development when the real MF/UF Membrane
Evaluation Unit hardware is unavailable.
"""

import json
import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.test_interfaces import SimulatedMEU
from system_control import HMI


def main() -> None:
    """Launch the MEU HMI with simulated hardware attached."""
    meu = SimulatedMEU()
    config_path = os.path.join(REPO_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            defaults = json.load(fp)
    except Exception:
        defaults = {}
    app = HMI(meu, fullscreen=True, defaults=defaults)
    app.mainloop()


if __name__ == "__main__":
    main()
