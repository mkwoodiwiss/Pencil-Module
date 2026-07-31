"""Hardware interfaces for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

import queue
import re
import threading
import time
from typing import Optional

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from . import serial_stub as serial

try:
    import lib8relind  # type: ignore
except Exception:  # pragma: no cover
    lib8relind = None

try:
    import multiio  # type: ignore
except Exception:  # pragma: no cover
    multiio = None


_WEIGHT_RE = re.compile(r"([ +-]?)\s*([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]+)")


class _RelayWrapper:
    """Wrap the 8-relay HAT functions with a small object API."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 0)


class _ScaleManager:
    """Own one scale serial port and serialize every read and command."""

    def __init__(
        self,
        port: str,
        baud: int,
        *,
        stale_after: float = 3.0,
        reconnect_after: float = 5.0,
    ) -> None:
        self.port = port
        self.baud = baud
        self.stale_after = stale_after
        self.reconnect_after = reconnect_after

        self.lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._commands: queue.Queue[tuple[str, object]] = queue.Queue()
        self._serial = None
        self._latest_text = "--"
        self._latest_value: Optional[float] = None
        self._latest_unit = "g"
        self._latest_time = 0.0
        self._last_open_attempt = 0.0
        self._last_error = ""
        self._print_pending = False

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    @property
    def serial(self):
        """Expose the current serial object for compatibility and diagnostics."""
        return self._serial

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
        now = time.monotonic()
        if not force and now - self._last_open_attempt < 1.0:
            return False
        self._last_open_attempt = now

        old_serial = self._serial
        self._serial = None
        if old_serial is not None:
            try:
                old_serial.close()
            except Exception:
                pass

        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.25)
            try:
                self._serial.reset_input_buffer()
            except Exception:
                pass
            self._last_error = ""
            return True
        except Exception as exc:
            self._last_error = repr(exc)
            self._serial = None
            return False

    def _close_serial(self) -> None:
        serial_connection = self._serial
        self._serial = None
        if serial_connection is not None:
            try:
                serial_connection.close()
            except Exception:
                pass

    def _readline(self) -> bytes:
        serial_connection = self._serial
        if serial_connection is None:
            return b""
        if hasattr(serial_connection, "readline"):
            return serial_connection.readline()
        return serial_connection.read_until(b"\r\n")

    def _write(self, command: bytes) -> bool:
        if self._serial is None and not self._open_serial(force=True):
            return False
        try:
            self._serial.write(command)
            try:
                self._serial.flush()
            except Exception:
                pass
            return True
        except Exception as exc:
            self._last_error = repr(exc)
            self._close_serial()
            return False

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
                if self._serial is None and not self._open_serial(force=True):
                    time.sleep(0.25)
                    continue

                try:
                    self._serial.reset_input_buffer()
                except Exception:
                    pass

                if not self._write(b"Z\r\n"):
                    time.sleep(0.25)
                    continue

                command_time = time.monotonic()
                deadline = command_time + float(timeout)
                consecutive_zero = 0

                while time.monotonic() < deadline and not self._stop_event.is_set():
                    try:
                        raw = self._readline()
                    except Exception as exc:
                        self._last_error = repr(exc)
                        self._close_serial()
                        break

                    parsed = self._parse(raw)
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
            self._write(b"P\r\n")
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

            if self._serial is None:
                self._open_serial()
                self._stop_event.wait(0.1)
                continue

            try:
                parsed = self._parse(self._readline())
                if parsed is not None:
                    self._record(parsed)
            except Exception as exc:
                self._last_error = repr(exc)
                self._close_serial()

            if self.age() > self.reconnect_after:
                self._open_serial()

        self._close_serial()

    def age(self) -> float:
        with self._state_lock:
            if self._latest_time <= 0:
                return float("inf")
            return time.monotonic() - self._latest_time

    def read(self) -> str:
        """Return the latest valid reading and queue one print request if stale."""
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
        """Queue a tare and wait for the serial-owner worker to verify it."""
        completed = threading.Event()
        result = {"success": False}
        self._commands.put(("tare", (result, completed, attempts, timeout)))
        completed.wait(attempts * (timeout + 1.0) + 2.0)
        return bool(result["success"])

    def health(self) -> dict:
        """Return diagnostic state for HMI messages and troubleshooting."""
        return {
            "port": self.port,
            "connected": self._serial is not None,
            "reading": self.read(),
            "age_seconds": self.age(),
            "last_error": self._last_error,
        }

    def close(self) -> None:
        self._commands.put(("stop", None))
        self._stop_event.set()
        self._thread.join(timeout=1.0)
        self._close_serial()


class MEU:
    """Interface to the MF/UF Membrane Evaluation Unit hardware."""

    SCALE_MANAGER_CLASS = _ScaleManager
    RELAY_WRAPPER_CLASS = _RelayWrapper

    def __init__(
        self,
        relay_stack: int = 1,
        io_stack: int = 2,
        effluent_port: str = "/dev/ttyAMA3",
        backwash_port: str = "/dev/ttyAMA2",
        baud: int = 9600,
        read_delay: float = 0.25,
    ) -> None:
        """Initialize scale, relay, and analog hardware interfaces."""
        scale_manager_class = self.SCALE_MANAGER_CLASS
        self._effluent_scale = scale_manager_class(effluent_port, baud)
        self._backwash_scale = scale_manager_class(backwash_port, baud)
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = read_delay
        self.relay = self.RELAY_WRAPPER_CLASS(relay_stack) if lib8relind else None
        self.io = self._create_multiio(io_stack)
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    @staticmethod
    def _create_multiio(io_stack: int):
        if not multiio:
            return None
        try:
            return multiio.SMmultiio(stack=io_stack, i2c=1)
        except Exception:  # pragma: no cover - hardware initialization failure
            return None

    def _scale_manager(self, channel: int):
        return self._effluent_scale if channel == 0 else self._backwash_scale

    @property
    def effluent_ser(self):
        return self._effluent_scale.serial

    @property
    def backwash_ser(self):
        return self._backwash_scale.serial

    def read_pressure(self, channel: int) -> float:
        """Return pressure in PSI from a 4-20 mA input channel."""
        if channel == 1:
            offset = self.pressure_offset_bw
        elif channel == 2:
            offset = self.pressure_offset_in
        else:
            offset = 0.0
        if self.io:
            ma = self.io.get_i_in(channel)
            return (ma - 4.0) * (30.0 / 16.0) + offset
        return offset

    def read_rtd(self, channel: int) -> float:
        """Return temperature from an RTD input channel."""
        if self.io:
            return self.io.get_rtd_temp(channel + 1) + self.temp_offset
        return self.temp_offset

    def set_solenoid(self, relay: int, state: bool) -> None:
        """Activate or deactivate a solenoid valve."""
        if self.relay:
            self.relay.on(relay) if state else self.relay.off(relay)

    def zero_scales(self) -> bool:
        """Tare both scales and return True only when both verify near zero."""
        return self.zero_scale(0) and self.zero_scale(1)

    def zero_scale(self, channel: int) -> bool:
        """Tare one scale through its serial-owner worker."""
        return self._scale_manager(channel).tare()

    def scale_health(self, channel: int) -> dict:
        """Return connection and freshness diagnostics for one scale."""
        return self._scale_manager(channel).health()

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Return the latest healthy cached reading from one scale."""
        return self._scale_manager(channel).read()

    def close(self) -> None:
        """Stop scale workers and close serial ports."""
        self._effluent_scale.close()
        self._backwash_scale.close()


PencilModule = MEU
