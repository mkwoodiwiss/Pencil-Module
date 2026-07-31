"""Launch the MEU HMI with deterministic Raspberry Pi hardware emulation."""

from __future__ import annotations

import os


def main() -> None:
    os.environ["MEU_EMULATE_RPI"] = "1"
    from system_control import main as run_application

    run_application()


if __name__ == "__main__":
    main()
