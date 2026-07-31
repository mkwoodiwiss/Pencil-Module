"""Highland scale protocol, command queue, and cached-reading ownership."""

from __future__ import annotations

import queue
import re
import threading
import time
from typing import Optional

from .serial_transport import SerialLineTransport


_WEIGHT_RE = re.compile(r"([ +-]?)\s*([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]+)")


class HighlandScaleManager:
    """Own Highland protocol state while delegating serial I/O to a transport."""

    TRANSPORT_CLASS = SerialLineTransport
    TARE_COMMAND = b"Z\r\n"
    PRINT_COMMAND = b"P\r\n"

    def __init__(
        self,
        port: str,
        baud: int,
        *,
        stale_after: float = 3.0,
        reconnect_after: float = 5.0,
        transport=None,
    ) -> None:
        self.port = port
        self.baud = baud
        self.stale_after = stale_after
        self.reconnect_after = reconnect_after
        self.lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._commands: queue.Queue[tuple[str, object]] = queue.Queue()
        self._transport = transport or self.TRANSPORT_CLASS(port, baud)
        self._latest_text = "--"
        self._latest_value: Optional[float] = None
        self._latest_unit = "g"
        self._latest_time = 0.0
        self._print_pending = False
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    @property
    def serial(self):
        return self._transport.connection

    @property
    def _serial(self):
        """Compatibility view for runtime subclasses and diagnostics."""
        return self._transport.connection

    @property
    def _last_error(self) -> str:
        return self._transport.last_error

    @_last_error.setter
    def _last_error(self, value: str) -> None:
        self._transport.last_error = value

    @staticmethod
    def _parse(raw: bytes | str) -> Optional[tuple[str, float, str]]:
        text = raw.decode("ascii", errors="ignore") if isinstance(raw, bytes) else raw
        match = _WEIGHT_RE.search(text)
        if not match:
            return None
        prefix, number, unit = match.groups()
        try:
            value = float(number)
        except ValueError:
            return None
        if prefix.strip() == "-" and value > 0:
            value = -value
        sign = "+" if value >= 0 else "-"
        return f"{sign}{abs(value):.1f} {unit}", value, unit

    def _open_serial(self, force: bool = False) -> bool:
        return self._transport.open(force=force)

    def _close_serial(self) -> None:
        self._transport.close()

    def _readline(self) -> bytes:
        return self._transport.readline()

    def _write(self, command: bytes) -> bool:
        return self._transport.write(command)

    def _reset_input_buffer(self) -> None:
        self._transport.reset_input_buffer()

    def _record(self, parsed: tuple[str, float, str]) -> None:
        text, value, unit = parsed
        with self._state_lock:
            self._latest_text = text
            self._latest_value = value
            self._latest_unit = unit
            self._latest_time = time.monotonic()

    def _process_tare(self, payload: object) -> None:
        result, completed, attempts, timeout = payload  # type: ignore[misc]
        success = False
        try:
            for _attempt in range(int(attempts)):
                if not self._transport.connected and not self._open_serial(force=True):
                    time.sleep(0.25)
                    continue
                self._reset_input_buffer()
                if not self._write(self.TARE_COMMAND):
                    time.sleep(0.25)
                    continue
                command_time = time.monotonic()
                deadline = command_time + float(timeout)
                consecutive_zero = 0
                while time.monotonic() < deadline and not self._stop_event.is_set():
                    try:
                        parsed = self._parse(self._readline())
                    except Exception:
                        break
                    if parsed is None:
                        continue
                    self._record(parsed)
                    _text, value, _unit = parsed
                    if time.monotonic() >= command_time and abs(value) <= 0.2:
                        consecutive_zero += 1
                        if consecutive_zero >= 2:
                            success = True
                            break
                    else:
                        consecutive_zero = 0
                if success:
                    break
                self._open_serial(force=True)
                time.sleep(0.25)
        finally:
            result["success"] = success
            completed.set()

    def _process_command(self, command: str, payload: object) -> None:
        if command == "tare":
            self._process_tare(payload)
        elif command == "print":
            self._write(self.PRINT_COMMAND)
            with self._state_lock:
                self._print_pending = False
        elif command == "reconnect":
            self._open_serial(force=True)
        elif command == "stop":
            self._stop_event.set()

    def _worker_loop(self) -> None:
        self._open_serial(force=True)
        while not self._stop_event.is_set():
            try:
                command, payload = self._commands.get_nowait()
            except queue.Empty:
                command = ""
                payload = None
            if command:
                self._process_command(command, payload)
                continue
            if not self._transport.connected:
                self._open_serial()
                self._stop_event.wait(0.1)
                continue
            try:
                parsed = self._parse(self._readline())
                if parsed is not None:
                    self._record(parsed)
            except Exception:
                pass
            if self.age() > self.reconnect_after:
                self._open_serial()
        self._close_serial()

    def age(self) -> float:
        with self._state_lock:
            if self._latest_time <= 0:
                return float("inf")
            return time.monotonic() - self._latest_time

    def read(self) -> str:
        with self._state_lock:
            text = self._latest_text
            timestamp = self._latest_time
            if timestamp > 0 and time.monotonic() - timestamp <= self.stale_after:
                return text
            if not self._print_pending:
                self._print_pending = True
                self._commands.put(("print", None))
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            with self._state_lock:
                if self._latest_time > timestamp:
                    return self._latest_text
            time.sleep(0.05)
        return "--"

    def tare(self, attempts: int = 3, timeout: float = 5.0) -> bool:
        completed = threading.Event()
        result = {"success": False}
        self._commands.put(("tare", (result, completed, attempts, timeout)))
        completed.wait(attempts * (timeout + 1.0) + 2.0)
        return bool(result["success"])

    def health(self) -> dict:
        return {
            "port": self.port,
            "connected": self._transport.connected,
            "reading": self.read(),
            "age_seconds": self.age(),
            "last_error": self._transport.last_error,
        }

    def close(self) -> None:
        self._commands.put(("stop", None))
        self._stop_event.set()
        self._thread.join(timeout=1.0)
        self._close_serial()


__all__ = ["HighlandScaleManager"]
