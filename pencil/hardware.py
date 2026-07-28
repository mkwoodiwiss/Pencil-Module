"""Hardware interface classes for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

import re
import threading
import time
from typing import Optional

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from . import serial_stub as serial

# Optional vendor libraries. These are unavailable in the test environment,
# so the code falls back to ``None`` which tests patch as needed.
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
    """Wrap the 8-relay HAT functions with a simple object API."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 0)


class _ScaleManager:
    """Continuously read, cache, monitor, and recover one serial scale."""

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
        self._serial = None
        self._latest_text = "--"
        self._latest_value: Optional[float] = None
        self._latest_unit = "g"
        self._latest_time = 0.0
        self._last_open_attempt = 0.0
        self._last_error = ""
        self._open_serial()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    @property
    def serial(self):
        """Expose the current serial object for compatibility and diagnostics."""
        return self._serial

    @staticmethod
    def _parse(raw: bytes | str) -> Optional[tuple[str, float, str]]:
        if isinstance(raw, bytes):
            text = raw.decode("ascii", errors="ignore")
        else:
            text = raw
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

    def _open_serial(self) -> bool:
        now = time.monotonic()
        if now - self._last_open_attempt < 1.0:
            return False
        self._last_open_attempt = now
        try:
            with self.lock:
                old = self._serial
                self._serial = None
                if old is not None:
                    try:
                        old.close()
                    except Exception:
                        pass
                self._serial = serial.Serial(self.port, self.baud, timeout=0.5)
                try:
                    self._serial.reset_input_buffer()
                except Exception:
                    pass
            self._last_error = ""
            return True
        except Exception as exc:
            self._last_error = repr(exc)
            return False

    def _readline(self) -> bytes:
        with self.lock:
            ser = self._serial
            if ser is None:
                return b""
            if hasattr(ser, "readline"):
                return ser.readline()
            return ser.read_until(b"\r\n")

    def _record(self, parsed: tuple[str, float, str]) -> None:
        text, value, unit = parsed
        with self._state_lock:
            self._latest_text = text
            self._latest_value = value
            self._latest_unit = unit
            self._latest_time = time.monotonic()

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._serial is None:
                self._open_serial()
                self._stop_event.wait(0.25)
                continue

            try:
                raw = self._readline()
                parsed = self._parse(raw)
                if parsed is not None:
                    self._record(parsed)
                    continue
            except Exception as exc:
                self._last_error = repr(exc)
                with self.lock:
                    try:
                        if self._serial is not None:
                            self._serial.close()
                    except Exception:
                        pass
                    self._serial = None

            age = self.age()
            if age > self.reconnect_after:
                self._open_serial()
            else:
                self._stop_event.wait(0.05)

    def age(self) -> float:
        with self._state_lock:
            if self._latest_time <= 0:
                return float("inf")
            return time.monotonic() - self._latest_time

    def read(self) -> str:
        """Return the newest valid reading, preserving brief stream dropouts."""
        with self._state_lock:
            text = self._latest_text
            timestamp = self._latest_time
        if timestamp > 0 and time.monotonic() - timestamp <= self.stale_after:
            return text

        # Prompt the scale only when its continuous stream has genuinely gone stale.
        self.send(b"P\r\n")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            with self._state_lock:
                if self._latest_time > timestamp:
                    return self._latest_text
            time.sleep(0.05)

        if self.age() > self.reconnect_after:
            self._open_serial()
        return "--"

    def send(self, command: bytes) -> bool:
        try:
            with self.lock:
                if self._serial is None and not self._open_serial():
                    return False
                self._serial.write(command)
                try:
                    self._serial.flush()
                except Exception:
                    pass
            return True
        except Exception as exc:
            self._last_error = repr(exc)
            with self.lock:
                try:
                    if self._serial is not None:
                        self._serial.close()
                except Exception:
                    pass
                self._serial = None
            return False

    def tare(self, attempts: int = 3, timeout: float = 3.0) -> bool:
        """Tare with retries and verify that fresh readings reach near zero."""
        commands = (b"Z\r\n", b"T\r\n")
        for attempt in range(attempts):
            before_time = self._latest_time
            command = commands[min(attempt, len(commands) - 1)]
            if not self.send(command):
                self._open_serial()
                time.sleep(0.25)
                continue

            deadline = time.monotonic() + timeout
            consecutive_zero = 0
            last_seen = before_time
            while time.monotonic() < deadline:
                with self._state_lock:
                    value = self._latest_value
                    reading_time = self._latest_time
                if reading_time > last_seen:
                    last_seen = reading_time
                    if value is not None and abs(value) <= 0.2:
                        consecutive_zero += 1
                        if consecutive_zero >= 2:
                            return True
                    else:
                        consecutive_zero = 0
                time.sleep(0.05)

            self._open_serial()
            time.sleep(0.25)
        return False

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
        self._stop_event.set()
        with self.lock:
            try:
                if self._serial is not None:
                    self._serial.close()
            except Exception:
                pass
            self._serial = None


class MEU:
    """Interface to the MF/UF Membrane Evaluation Unit hardware."""

    def __init__(
        self,
        relay_stack: int = 1,
        io_stack: int = 2,
        effluent_port: str = "/dev/ttyAMA3",
        backwash_port: str = "/dev/ttyAMA2",
        baud: int = 9600,
        read_delay: float = 0.25,
    ) -> None:
        """Initialize connections to the MEU hardware."""
        self._effluent_scale = _ScaleManager(effluent_port, baud)
        self._backwash_scale = _ScaleManager(backwash_port, baud)
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = read_delay
        if lib8relind:
            self.relay = _RelayWrapper(relay_stack)
        else:
            self.relay = None
        if multiio:
            try:
                self.io = multiio.SMmultiio(stack=io_stack, i2c=1)
            except Exception:  # pragma: no cover - hardware init failed
                self.io = None
        else:
            self.io = None
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

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
            psi = (ma - 4.0) * (30.0 / 16.0)
            return psi + offset
        return offset

    def read_rtd(self, channel: int) -> float:
        """Return temperature from an RTD input channel."""
        if self.io:
            temp = self.io.get_rtd_temp(channel + 1)
            return temp + self.temp_offset
        return self.temp_offset

    def set_solenoid(self, relay: int, state: bool) -> None:
        """Activate or deactivate a solenoid valve."""
        if self.relay:
            if state:
                self.relay.on(relay)
            else:
                self.relay.off(relay)

    def zero_scales(self) -> bool:
        """Tare both scales and return True only when both verify near zero."""
        effluent_ok = self.zero_scale(0)
        backwash_ok = self.zero_scale(1)
        return effluent_ok and backwash_ok

    def zero_scale(self, channel: int) -> bool:
        """Tare one scale with retries, verification, and reconnection."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.tare()

    def scale_health(self, channel: int) -> dict:
        """Return connection and freshness diagnostics for one scale."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.health()

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        """Store calibration offsets for later readings."""
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Return the latest healthy cached reading from one scale."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.read()

    def close(self) -> None:
        """Stop scale workers and close serial ports."""
        self._effluent_scale.close()
        self._backwash_scale.close()


# Backward-compatible alias for older scripts and saved integrations.
PencilModule = MEU
