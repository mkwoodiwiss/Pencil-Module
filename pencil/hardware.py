"""Hardware interface classes for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

import re
import string
import time
import threading
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


class _RelayWrapper:
    """Wrap the 8-relay HAT functions with a simple object API."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 0)


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
        self.effluent_ser = serial.Serial(effluent_port, baud, timeout=1)
        self.backwash_ser = serial.Serial(backwash_port, baud, timeout=1)
        self.effluent_lock = threading.Lock()
        self.backwash_lock = threading.Lock()
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

    def zero_scales(self) -> None:
        """Issue a zero command to both scales."""
        self.zero_scale(0)
        self.zero_scale(1)

    def zero_scale(self, channel: int) -> None:
        """Zero an individual scale."""
        ser = self.effluent_ser if channel == 0 else self.backwash_ser
        lock = self.effluent_lock if channel == 0 else self.backwash_lock
        cmd = b"Z\r\n"
        try:
            with lock:
                ser.write(cmd)
        except Exception:
            pass

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
        """Return the weight from one of the scales."""
        ser = self.effluent_ser if channel == 0 else self.backwash_ser
        lock = self.effluent_lock if channel == 0 else self.backwash_lock
        cmd = b"P\r\n"
        try:
            with lock:
                try:
                    ser.reset_input_buffer()
                except Exception:
                    pass
                ser.write(cmd)
                time.sleep(self._read_delay)
                response = ser.read_until(b"\r\n").decode("ascii", errors="ignore")
            cleaned = "".join(c for c in response if c in string.printable)
            match = re.search(r"([ +-])\s*([\d\.]+)\s*([a-zA-Z]+)", cleaned)
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


# Backward-compatible alias for older scripts and saved integrations.
PencilModule = MEU
