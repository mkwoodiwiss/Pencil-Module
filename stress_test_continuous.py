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

from scripts.weight_reader import parse_weight_line




def log_message(log_file: Path, msg: str) -> None:
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    with open(log_file, "a") as fh:
        fh.write(f"{timestamp} {msg}\n")


def poll_scale(
    name: str,
    ser: serial.Serial,
    log_file: Path,
    stop: threading.Event,
    counts: dict[str, int],
) -> None:
    while not stop.is_set():
        try:
            line = ser.readline()
            if not line:
                log_message(log_file, f"{name}: read timeout | RAW: '' | HEX: ''")
                counts[name] += 1
            else:
                ascii_text = line.decode("ascii", errors="ignore").strip()
                hex_text = line.hex()
                result = parse_weight_line(line)
                if result == "--":
                    log_message(
                        log_file,
                        f"{name}: invalid '{ascii_text}' | RAW: '{ascii_text}' | HEX: '{hex_text}'",
                    )
                else:
                    log_message(
                        log_file,
                        f"{name}: {result} | RAW: '{ascii_text}' | HEX: '{hex_text}'",
                    )
        except Exception as exc:  # pragma: no cover - runtime errors
            log_message(log_file, f"{name}: error {exc}")
        stop.wait(0.25)


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
    log_file = Path("logs") / (
        f"usb_scale_stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    # Use the Pi's built-in RS232 ports for the weight scales
    effluent_ser = serial.Serial("/dev/ttyAMA3", 9600, timeout=0.1)
    backwash_ser = serial.Serial("/dev/ttyAMA2", 9600, timeout=0.1)

    stop = threading.Event()
    counts = {"Effluent": 0, "Backwash": 0}
    eff_thread = threading.Thread(
        target=poll_scale,
        args=("Effluent", effluent_ser, log_file, stop, counts),
        daemon=True,
    )
    bw_thread = threading.Thread(
        target=poll_scale,
        args=("Backwash", backwash_ser, log_file, stop, counts),
        daemon=True,
    )

    bw_thread.start()
    time.sleep(0.125)
    eff_thread.start()

    threads = [eff_thread, bw_thread]

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        log_message(log_file, "Interrupted by user")
    finally:
        stop.set()
        for t in threads:
            t.join()
        effluent_ser.close()
        backwash_ser.close()
        summary = (
            f"Effluent timeouts: {counts['Effluent']} | Backwash timeouts: {counts['Backwash']}"
        )
        log_message(log_file, summary)
        print(summary)


if __name__ == "__main__":
    main()
