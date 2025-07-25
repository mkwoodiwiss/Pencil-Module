import argparse
import threading
import time
from datetime import datetime
from pathlib import Path
import sys

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when pyserial missing
    from pencil import serial_stub as serial

# Ensure repo root on path when run from scripts directory
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.weight_reader import read_weight


class _LineSerial:
    """Minimal wrapper to reuse read_weight() for parsing lines."""

    def __init__(self, line: bytes):
        self._line = line

    def reset_input_buffer(self) -> None:  # noqa: D401 - mimic serial API
        pass

    def write(self, data: bytes) -> None:
        # read_weight() will attempt to send the poll command. Ignore it.
        pass

    def read_until(self, sep: bytes = b"\r\n") -> bytes:
        return self._line


def parse_weight_line(line: bytes) -> str:
    """Parse a single weight line using ``read_weight`` logic."""
    return read_weight(_LineSerial(line))


def log_message(log_file: Path, msg: str) -> None:
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    with open(log_file, "a") as fh:
        fh.write(f"{timestamp} {msg}\n")


def poll_scale(name: str, ser: serial.Serial, log_file: Path, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            line = ser.readline()
            if not line:
                log_message(log_file, f"{name}: read timeout")
            else:
                result = parse_weight_line(line)
                text = line.decode("ascii", errors="ignore").strip()
                if result == "--":
                    log_message(log_file, f"{name}: invalid '{text}'")
                else:
                    log_message(log_file, f"{name}: {result}")
        except Exception as exc:  # pragma: no cover - runtime errors
            log_message(log_file, f"{name}: error {exc}")
        stop.wait(0.1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Continuous scale stress test")
    parser.add_argument(
        "duration",
        type=float,
        nargs="?",
        default=60.0,
        help="Test duration in seconds (default: 60)",
    )
    args = parser.parse_args(argv)

    Path("logs").mkdir(exist_ok=True)
    log_file = Path("logs") / f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    effluent_ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=0.1)
    backwash_ser = serial.Serial("/dev/ttyUSB1", 9600, timeout=0.1)

    stop = threading.Event()
    threads = [
        threading.Thread(target=poll_scale, args=("Effluent", effluent_ser, log_file, stop), daemon=True),
        threading.Thread(target=poll_scale, args=("Backwash", backwash_ser, log_file, stop), daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for t in threads:
            t.join()
        effluent_ser.close()
        backwash_ser.close()


if __name__ == "__main__":
    main()
