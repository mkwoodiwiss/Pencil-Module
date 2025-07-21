"""Simple test script for the Sequent Multi IO hat.

This assumes the hardware and vendor drivers are installed. It reads the
4-20 mA inputs on channels 1 and 2 as well as the RTD sensors on channels
1 and 2. The script provides a very small interactive CLI similar to the
``weight_reader.py`` helper.
"""

import sys
from typing import Any

try:
    import multiio  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - running without drivers
    sys.exit(f"multiio driver not available: {exc}")


def main(stack: int = 2, i2c: int = 1) -> None:
    """Interactive command line interface for reading the sensors."""
    io = multiio.SMmultiio(stack=stack, i2c=i2c)

    menu = (
        "Enter 'a' to read 4-20mA channels, 'r' to read RTD channels, or 'q' to quit: "
    )
    while True:
        try:
            choice = input(menu).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice.startswith("q"):
            break
        elif choice.startswith("a"):
            ch1 = io.get_i_in(1)
            ch2 = io.get_i_in(2)
            print(f"Channel 1: {ch1:.2f} mA")
            print(f"Channel 2: {ch2:.2f} mA")
        elif choice.startswith("r"):
            rtd1 = io.get_rtd_temp(1)
            rtd2 = io.get_rtd_temp(2)
            print(f"RTD 1: {rtd1:.2f} C")
            print(f"RTD 2: {rtd2:.2f} C")


if __name__ == "__main__":
    main()
