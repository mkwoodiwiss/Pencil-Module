"""Run the GUI using simulated hardware for manual testing."""

from tests.test_interfaces import SimulatedPencilModule
from system_control import HMI


def main() -> None:
    module = SimulatedPencilModule()
    app = HMI(module)
    app.mainloop()


if __name__ == "__main__":
    main()
