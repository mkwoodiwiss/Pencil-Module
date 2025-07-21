"""Run the GUI using simulated hardware for manual testing.

This helper script is useful during development when the real
hardware is not available. It imports the simulated interfaces from
the test suite and instantiates the normal :class:`HMI` so the user
can interact with the GUI.
"""

from tests.test_interfaces import SimulatedPencilModule
from system_control import HMI


def main() -> None:
    """Launch the HMI with simulated hardware attached."""
    module = SimulatedPencilModule()
    app = HMI(module, fullscreen=True)
    app.mainloop()


if __name__ == "__main__":
    main()
