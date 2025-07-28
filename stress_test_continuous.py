import argparse
import os
import subprocess
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


log_buffer: list[str] = []
log_lock = threading.Lock()


def log_message(log_file: Path, msg: str, enable_file: bool = True) -> None:
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    entry = f"{timestamp} {msg}"
    print(entry)
    if enable_file:
        with log_lock:
            log_buffer.append(entry)


def flush_log_buffer(log_file: Path, stop: threading.Event, enable_file: bool) -> None:
    while not stop.is_set():
        time.sleep(1)
        if not enable_file:
            continue
        with log_lock:
            if log_buffer:
                with open(log_file, "a") as fh:
                    fh.write("\n".join(log_buffer) + "\n")
                log_buffer.clear()


def poll_scale(
    name: str,
    ser: serial.Serial,
    log_file: Path,
    stop: threading.Event,
    counts: dict[str, int],
    enable_file: bool,
) -> None:
    buffer = bytearray()
    while not stop.is_set():
        try:
            chunk = ser.read(64)
            if chunk:
                buffer.extend(chunk)
                while b"\r\n" in buffer:
                    line, _, buffer = buffer.partition(b"\r\n")
                    ascii_text = line.decode("ascii", errors="ignore")
                    hex_text = line.hex()
                    result = parse_weight_line(line + b"\r\n")
                    if result == "--":
                        log_message(
                            log_file,
                            f"{name}: invalid '{ascii_text}' | RAW: '{ascii_text}' | HEX: '{hex_text}'",
                            enable_file,
                        )
                    else:
                        log_message(
                            log_file,
                            f"{name}: {result} | RAW: '{ascii_text}' | HEX: '{hex_text}'",
                            enable_file,
                        )
            else:
                counts[name] += 1
                log_message(log_file, f"{name}: read timeout", enable_file)
        except Exception as exc:  # pragma: no cover - runtime errors
            log_message(log_file, f"{name}: error {exc}", enable_file)
        time.sleep(0.001)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Continuous scale stress test")
    parser.add_argument(
        "duration",
        type=float,
        nargs="?",
        default=60.0,
        help="Test duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable file logging for maximum speed",
    )
    args = parser.parse_args(argv)

    try:
        subprocess.run(["chrt", "-f", "99", str(os.getpid())], check=True)
    except Exception:
        pass

    Path("logs").mkdir(exist_ok=True)
    log_file = Path("logs") / (
        f"usb_scale_stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    enable_file = not args.no_log

    # Use the Pi's built-in RS232 ports for the weight scales
    effluent_ser = serial.Serial("/dev/ttyAMA3", 9600, timeout=0.05)
    backwash_ser = serial.Serial("/dev/ttyAMA2", 9600, timeout=0.05)

    stop = threading.Event()
    counts = {"Effluent": 0, "Backwash": 0}
    eff_thread = threading.Thread(
        target=poll_scale,
        args=("Effluent", effluent_ser, log_file, stop, counts, enable_file),
        daemon=True,
    )
    bw_thread = threading.Thread(
        target=poll_scale,
        args=("Backwash", backwash_ser, log_file, stop, counts, enable_file),
        daemon=True,
    )
    flush_thread = threading.Thread(
        target=flush_log_buffer,
        args=(log_file, stop, enable_file),
        daemon=True,
    )

    bw_thread.start()
    time.sleep(0.125)
    eff_thread.start()
    flush_thread.start()

    threads = [eff_thread, bw_thread, flush_thread]

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        log_message(log_file, "Interrupted by user", enable_file)
    finally:
        stop.set()
        for t in threads:
            t.join()
        effluent_ser.close()
        backwash_ser.close()
        summary = (
            f"Effluent timeouts: {counts['Effluent']} | Backwash timeouts: {counts['Backwash']}"
        )
        log_message(log_file, summary, enable_file)
        print(summary)


if __name__ == "__main__":
    main()
