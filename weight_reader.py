import re
import time
import serial


def read_weight(port="/dev/ttyUSB0", baud=9600) -> str:
    """Return the weight string from the scale or '--' on error."""
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            ser.write(b"P\r\n")
            time.sleep(0.1)
            response = ser.read_until(b"\r\n").decode("ascii", errors="ignore").strip()
            match = re.search(r"([±+-]?)(\d+\.\d+)\s*(\w)", response)
            if match:
                sign = match.group(1) if match.group(1) else "+"
                value = match.group(2)
                unit = match.group(3)
                return f"{sign}{value} {unit}"
    except Exception:
        pass
    return "--"


def zero_scale(port="/dev/ttyUSB0", baud=9600) -> None:
    """Send the zero command to the scale."""
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            ser.write(b"Z\r\n")
    except Exception:
        pass


def main() -> None:
    """Interactive CLI for reading or zeroing the scale."""
    while True:
        try:
            choice = input(
                "Enter 'r' to read weight, 'z' to zero the scale, or 'q' to quit: "
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if choice.startswith("r"):
            print("Weight:", read_weight())
        elif choice.startswith("z"):
            zero_scale()
            print("Scale zeroed")
        elif choice.startswith("q"):
            break


if __name__ == "__main__":
    main()
