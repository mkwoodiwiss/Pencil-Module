import re
import time
import serial
import string


def read_weight(ser: serial.Serial) -> str:
    """Return the weight string from the scale or '--' on error."""
    try:
        print("Resetting input buffer...")
        ser.reset_input_buffer()
        print("Sending 'P' command to scale...")
        ser.write(b"P\r\n")
        time.sleep(0.1)
        print("Reading response from scale...")
        response = ser.read_until(b"\r\n").decode("ascii", errors="ignore")
        print(f"Raw response: {repr(response)}")
        # Remove all non-printable characters
        cleaned = ''.join(c for c in response if c in string.printable)
        print(f"Cleaned response: {repr(cleaned)}")
        # Always parse from the start: sign, value, unit
        if len(cleaned) >= 10:
            sign = cleaned[0]
            value = cleaned[1:9].strip()
            unit = cleaned[9]
            if sign == " ":
                sign = "+"
            print(f"Parsed: sign={sign}, value={value}, unit={unit}")
            return f"{sign}{value} {unit}"
        print("Response too short or unexpected format.")
    except Exception as e:
        print(f"Error reading weight: {e}")
    return "--"

def zero_scale(ser: serial.Serial) -> None:
    """Send the zero command to the scale."""
    try:
        print("Sending 'Z' command to zero the scale...")
        ser.write(b"Z\r\n")
    except Exception as e:
        print(f"Error zeroing the scale: {e}")

def main(port: str = "/dev/ttyUSB0", baud: int = 9600) -> None:
    """Interactive CLI for reading or zeroing the scale."""
    print(f"Opening serial port {port} at {baud} baud...")
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
