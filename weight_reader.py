import re
import time
import serial
import logging


def read_weight(ser: serial.Serial) -> str:
    """Return the weight string from the scale or '--' on error."""
    try:
        ser.reset_input_buffer()
        ser.write(b"P\r\n")
        time.sleep(0.1)
        response = ser.read_until(b"\r\n").decode("ascii", errors="ignore").strip()
        # Match: sign (space or -), optional spaces, digits, dot, digits, space, unit
        match = re.match(r"([ -])\s*(\d+\.\d+)\s*(\w)", response)
        if match:
            sign = "+" if match.group(1) == " " else "-"
            value = match.group(2)
            unit = match.group(3)
            return f"{sign}{value} {unit}"
    except Exception as e:
        logging.error("Error reading weight from scale: %s", e)
        logging.exception("Error reading weight from scale")
    return "--"

def zero_scale(ser: serial.Serial) -> None:
    """Send the zero command to the scale."""
    try:
        ser.write(b"Z\r\n")
    except Exception as e:
        logging.error("Error zeroing the scale: %s", e)


def main(port: str = "/dev/ttyUSB0", baud: int = 9600) -> None:
    """Interactive CLI for reading or zeroing the scale."""
    with serial.Serial(port, baud, timeout=1) as ser:
        try:
            ser.reset_input_buffer()
        except Exception as e:
            print(f"Warning: Could not reset input buffer: {e}")
        while True:
            try:
                choice = input(
                    "Enter 'r' to read weight, 'z' to zero the scale, or 'q' to quit: "
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if choice.startswith("r"):
                print("Weight:", read_weight(ser))
            elif choice.startswith("z"):
                zero_scale(ser)
                print("Scale zeroed")
            elif choice.startswith("q"):
                break


if __name__ == "__main__":
    main()
