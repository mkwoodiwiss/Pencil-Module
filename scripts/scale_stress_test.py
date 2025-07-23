import threading
import time
from datetime import datetime

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when pyserial is missing
    from pencil import serial_stub as serial

from scripts.weight_reader import read_weight


log_lock = threading.Lock()


def log(msg: str) -> None:
    """Write a timestamped message to the log file in a thread-safe way."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    with log_lock:
        with open("scale_stress_test.log", "a") as fh:
            fh.write(f"{timestamp} {msg}\n")


def poll_scale(name: str, ser: serial.Serial, stop: threading.Event) -> None:
    """Continuously query a scale until the stop event is set."""
    while not stop.is_set():
        try:
            result = read_weight(ser)
        except Exception as exc:  # pragma: no cover - runtime exceptions
            result = f"error: {exc}"
        log(f"{name}: {result}")
        for _ in range(10):
            if stop.is_set():
                break
            time.sleep(0.01)


def main() -> None:
    stop = threading.Event()
    effluent_ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
    backwash_ser = serial.Serial("/dev/ttyUSB1", 9600, timeout=1)

    threads = [
        threading.Thread(
            target=poll_scale,
            args=("Effluent", effluent_ser, stop),
            daemon=True,
        ),
        threading.Thread(
            target=poll_scale,
            args=("Backwash", backwash_ser, stop),
            daemon=True,
        ),
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
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
