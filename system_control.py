"""High level controller for the Pencil Module."""

from pencil import (
    FiltrationConfig,
    FiltrationTestSystem,
    HMI,
    PencilModule,
)


def main() -> None:
    """Entry point when running the module directly."""
    module = PencilModule()
    app = HMI(module, fullscreen=True)
    app.mainloop()


if __name__ == "__main__":
    main()
