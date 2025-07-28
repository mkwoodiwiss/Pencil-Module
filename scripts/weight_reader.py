import time
try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when pyserial is missing
    from pencil import serial_stub as serial
import string
import re


def _parse_text(text: str) -> str:
    """Return formatted weight from a raw response string."""
    cleaned = ''.join(c for c in text if c in string.printable)
    match = re.search(r'([ +-])\s*([\d\.]+)\s*([a-zA-Z]+)', cleaned)
    if match:
        sign, value, unit = match.groups()
        if sign == " ":
            sign = "+"
        return f"{sign}{value} {unit}"
    return "--"


def read_weight(ser: serial.Serial) -> str:
    """
    Query the scale for the current weight and return a formatted string.
    Returns '--' if parsing fails.

    The scale response format is:
      [sign][7 chars value][space][unit][spaces][CR][LF]
    Example: '+   13.10 g   \r\n' or '-   13.10 g   \r\n'
    """
    try:
        ser.reset_input_buffer()
        ser.write(b"P\r\n")
        time.sleep(0.1)
        response = ser.read_until(b"\r\n").decode("ascii", errors="ignore")
        return _parse_text(response)
    except Exception:
        pass
    return "--"


def zero_scale(ser: serial.Serial) -> None:
    """
    Send the zero command to the scale.
    """
    try:
        ser.write(b"Z\r\n")
    except Exception:
        pass


def parse_weight_line(line: bytes) -> str:
    """Return a formatted weight from a line emitted by the scale."""
    try:
        text = line.decode("ascii", errors="ignore")
    except Exception:
        return "--"
    return _parse_text(text)


def main(port: str = "/dev/ttyAMA3", baud: int = 9600) -> None:
    """
    Interactive CLI for reading or zeroing the scale.
    """
    with serial.Serial(port, baud, timeout=1) as ser:
        try:
            ser.reset_input_buffer()
        except Exception:
            pass
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
