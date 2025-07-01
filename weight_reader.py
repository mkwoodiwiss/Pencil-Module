import time
import serial
import string
import re


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
        # Remove all non-printable characters except space
        cleaned = ''.join(c for c in response if c in string.printable)
        # Use regex to extract sign, value, and unit
        match = re.search(r'([ +-])\s*([\d\.]+)\s*([a-zA-Z]+)', cleaned)
        if match:
            sign = match.group(1)
            value = match.group(2)
            unit = match.group(3)
            if sign == " ":
                sign = "+"
            return f"{sign}{value} {unit}"
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


def main(port: str = "/dev/ttyUSB0", baud: int = 9600) -> None:
    """
    Interactive CLI for reading or zeroing the scale.
    """
    print(f"Opening serial port {port} at {baud} baud...")
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
